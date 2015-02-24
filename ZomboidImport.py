import bpy,io,bmesh
from bpy import context
from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector
from mathutils import Matrix
from mathutils import Quaternion
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
import math

class ZomboidImport(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    
    # important since its how bpy.ops.import_test.some_data is constructed
    bl_idname = "zomboid.import_model"
    bl_label = "Import a Zomboid Model"
    
    # Get the current scene
    scene = context.scene

    def read_header(self,file):
        self.version = self.read_float(file)
        self.modelName = self.read_line(file)
        self.amtname = self.modelName + "_armature"
        self.vertexStrideElementCount = self.read_int(file)
        self.vertexStrideSize = self.read_int(file)

    # Vertex Stride Data:
    # (Int)     Offset
    # (String)  
    def read_stride_data(self,file):

        for x in range(0,self.vertexStrideElementCount):
            
            value = self.read_line(file)
            
            type = self.read_line(file)
            
            self.vertexStrideType.append(type)
            
            if type == "TextureCoordArray":
                self.hasTex = True
            
            # Place it in the dictionary
            self.vertexStrideData[type] = value

    def read_vertex_buffer(self,file):
        for x in range(0,int(self.vertexCount)):
        
            elementArray = []
        
            for element in range(0,self.vertexStrideElementCount):
                                
                if self.vertexStrideType[element] == "VertexArray":
                    
                    line = self.read_line(file)
                    vs = line.split(', ')

                    self.verts.append(Vector((float(vs[0]), float(vs[1]), float(vs[2]))))

                elif self.vertexStrideType[element] == "TextureCoordArray":
                    line = self.read_line(file)
                    vs = line.split(', ')

                    self.uvs.append(Vector((float(vs[0]),float(1) - float(vs[1]))))
                    
                elif self.vertexStrideType[element] == "BlendWeightArray":
                    self.read_vertex_weight_values(file)
                elif self.vertexStrideType[element] == "BlendIndexArray":
                    self.read_vertex_weight_indexes(file)
                else:
                    line = self.read_line(file)
                    
    def read_faces(self,file):
        for x in range(0,self.numberOfFaces):
            
            face = self.read_line(file)
            
            faceVerts = face.split(", ")
            
            faceVerts[0] = int(faceVerts[0])
            faceVerts[1] = int(faceVerts[1])
            faceVerts[2] = int(faceVerts[2])
            
            if self.hasTex:
                self.faceUVs.append([self.uvs[faceVerts[0]],self.uvs[faceVerts[1]],self.uvs[faceVerts[2]]])
            
            self.faces.append([faceVerts[0], faceVerts[1], faceVerts[2]])
                                    
            self.faceBuffer.append(faceVerts)

    def read_bone_hierarchy(self,file):
        for index in range(0,self.numberBones):
            
            boneIndex = self.read_int(file)
            boneParentIndex = self.read_int(file)
            boneName = self.read_line(file)
            
            self.bone_ids[boneName] = boneIndex
            
            self.bone_names.append(boneName)
            self.bone_parent.append(boneParentIndex)

    # Bind Pose:
    # (Int)    Bone Index
    # (Matrix) Bind Matrix
    def read_bone_bind_pose_data(self,file):
        
        for index in range(0,self.numberBones):
            
            boneIndex = self.read_int(file)
                        
            bone_matrix = self.read_matrix(file)
            
            self.bone_matrix_bind_pose_data[index] = bone_matrix
            

    def read_bone_bind_inverse_pose_data(self,file):
        
        for index in range(0,self.numberBones):
        
            boneIndex = self.read_int(file)
        
            matrix_inverse = self.read_matrix(file)
            
            self.bone_matrix_inverse_bind_pose_data[index] = matrix_inverse


    def read_bone_offset_data(self,file):
        
        for index in range(0,self.numberBones):
        
            boneIndex = self.read_int(file)
            
            bone_offset_matrix = self.read_matrix(file)
            
            self.bone_matrix_offset_data[index] = bone_offset_matrix
            

    def create_mesh(self):
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            ok = True
        
        try:
            bpy.ops.object.select_all(action='DESELECT')
        except:
            ok = True
        
        mesh = bpy.data.meshes.new(name=self.modelName)
        mesh.from_pydata(self.verts, self.edges, self.faces)
        mesh.update(calc_tessface=True)

        object_data_add(context, mesh)
        
        bpy.ops.object.select_pattern(pattern=self.modelName)
        obj = bpy.context.active_object
        me = obj.data
        
        bpy.ops.object.mode_set(mode = 'EDIT')

        bm = bmesh.from_edit_mesh(me)

        # currently blender needs both layers.
        uv_layer = bm.loops.layers.uv.verify()
        bm.faces.layers.tex.verify()

        voffset = 0
        # adjust UVs
        for f in bm.faces:
            index = f.index
            uv_array = self.faceUVs[index]
            vo = 0
            for l in f.loops:
                luv = l[uv_layer]
                luv.uv = uv_array[vo]
                vo += 1
        
        bmesh.update_edit_mesh(me)
        
        if self.has_armature:
            obj_armature = bpy.data.objects[self.amtname]
            
            
            bpy.ops.object.select_pattern(pattern=self.modelName)
            obj.parent = obj_armature
            obj.parent_type = 'ARMATURE'
            modifier = bpy.ops.object.modifier_add(type='ARMATURE')
            
            bpy.ops.object.mode_set(mode = 'OBJECT')
            
            for bone in self.armature.bones:
                bpy.ops.object.vertex_group_add()
                vertex_group = obj.vertex_groups.active    
                vertex_group.name = bone.name
                
                bone_import_index = self.bone_ids[bone.name]
                
                
                
                offset_vert = 0
                for vertex in me.vertices:
                    vertex_weight_ids = self.BlendIndexArray[offset_vert]
                    vertex_weights = self.BlendWeightArray[offset_vert]
                    
                    offset = 0
                    for vert_weight_id in vertex_weight_ids:
                        if vert_weight_id == bone_import_index:
                            verts = []
                            verts.append(vertex.index)
                            vertex_group.add(verts, vertex_weights[offset], 'REPLACE')
                        offset += 1
                    
                    offset_vert += 1

        bpy.ops.object.mode_set(mode = 'EDIT')

        # Optimize mesh
        bpy.ops.mesh.remove_doubles()
        bpy.ops.mesh.tris_convert_to_quads()
        bpy.ops.object.mode_set(mode = 'OBJECT')


    def create_armature(self):
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
        except:
            ok = None
        
        self.armature = bpy.data.armatures.new(self.amtname)
        ob = bpy.data.objects.new(self.amtname, self.armature)
        scn = bpy.context.scene
        scn.objects.link(ob)
        scn.objects.active = ob
        ob.select = True
        
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        
        bone = self.armature.edit_bones.new(self.bone_names[0])
        self.bones.append(bone)
        matrix_location = self.bone_matrix_offset_data[0]
        mat = Matrix.Identity(4)
        self.set_identity(mat)
        
        mat_world = matrix_location * mat
        self.world_transforms.append(mat_world)
        
        bone.matrix = mat_world
        bone.tail = Vector((bone.head[0], bone.head[1] + 0.05, bone.head[2]))
        
        for x in range(1, self.numberBones):
            
            bone = self.armature.edit_bones.new(self.bone_names[x])
            self.bones.append(bone)
            
            parent_index = self.bone_parent[x]
            
            parent_bone = self.bones[parent_index]

            
            matrix_location = self.bone_matrix_offset_data[x]
            matrix_rotation = self.bone_matrix_inverse_bind_pose_data[x]
            
            mat_world = matrix_location * self.bone_matrix_offset_data[parent_index].copy().inverted()
            
            
            self.world_transforms.append(mat_world)
            
            mat = matrix_location.inverted().copy()
            
            # bone.tail = mat.decompose()[0]
            # bone.head = parent_bone.tail
            
            bone.head = mat.decompose()[0]
            bone.tail = Vector((bone.head[0], bone.head[1] + 0.05, bone.head[2]))
            
            if parent_index != -1:
                if bone.tail[0] == 0 and bone.tail[1] == 0 and bone.tail[2] == 0:
                    bone.tail = Vector((bone.head[0], bone.head[1] + 0.05, bone.head[2]))

            bone.parent = parent_bone
            # bone.use_connect = True
        
        obj_armature = bpy.data.objects[self.amtname]
        obj_armature.show_x_ray = True
            

    def read_int(self,file):
        return int(self.read_line(file))


    def read_float(self,file):
        return float(self.read_line(file))


    def read_line(self,file):
        string = '#'
        while string.startswith("#"):
            string = str(file.readline().strip())
        return string


    def read_matrix(self,file):
        matrix_line = []
        for i in range(0,4):
            matrix_array = []
            string_mat = self.read_line(file).split(", ")
            matrix_array.append(float(string_mat[0]))
            matrix_array.append(float(string_mat[1]))
            matrix_array.append(float(string_mat[2]))
            matrix_array.append(float(string_mat[3]))
            matrix_line.append((matrix_array[0],matrix_array[1],matrix_array[2],matrix_array[3]))
        return Matrix((matrix_line[0], matrix_line[1], matrix_line[2], matrix_line[3]))
    
    def read_vertex_weight_values(self,file):
        weights = self.read_line(file)
        split = weights.split(", ")
        
        array = []
        
        for s in split:
            array.append(float(s))
        
        self.BlendWeightArray.append(array)
    
    def read_vertex_weight_indexes(self,file):
        indexes = self.read_line(file)
        split = indexes.split(", ")
        array = []
        for s in split:
            array.append(int(s))
        self.BlendIndexArray.append(array)
        
    def set_identity(self, mat):
        mat[0][0] = 1.0
        mat[0][1] = 0.0
        mat[0][2] = 0.0
        mat[0][3] = 0.0
        mat[1][0] = 0.0
        mat[1][1] = 1.0
        mat[1][2] = 0.0
        mat[1][3] = 0.0
        mat[2][0] = 0.0
        mat[2][1] = 0.0
        mat[2][2] = 1.0
        mat[2][3] = 0.0
        mat[3][0] = 0.0
        mat[3][1] = 0.0
        mat[3][2] = 0.0
        mat[3][3] = 1.0

    def execute(self, context):
        
        old_cursor = bpy.context.scene.cursor_location
        
        # Center the cursor.
        bpy.context.scene.cursor_location = (0.0, 0.0, 0.0)
        
        # The offset in the file read
        offset = 0

        with io.open(self.filepath, 'r') as file:
            end_of_file = False
            while file.readable():
                    if offset == 0:
                        self.read_header(file)
                    elif offset == 1:
                        self.read_stride_data(file)
                    elif offset == 2:
                        self.vertexCount = self.read_int(file)
                    elif offset == 3:
                        self.read_vertex_buffer(file)
                    elif offset == 4:
                        self.numberOfFaces = self.read_int(file)
                    elif offset == 5:
                        self.read_faces(file)
                    elif offset == 6:
                        try:
                            self.numberBones = self.read_int(file)
                            self.has_armature = True
                        except:
                            end_of_file = True
                    elif offset == 7:
                        self.read_bone_hierarchy(file)
                    elif offset == 8:
                        self.read_bone_bind_pose_data(file)
                    elif offset == 9:
                        self.read_bone_bind_inverse_pose_data(file)
                    elif offset == 10:
                        self.read_bone_offset_data(file)
                    offset+=1
                    if offset > 13 or end_of_file:
                        break
                    
            # Close the file.
            file.close()
        
        if self.has_armature:
            self.create_armature()
        
        self.create_mesh()
        
        bpy.context.scene.cursor_location = old_cursor
        
        return {'FINISHED'}
        
    def __init__(self):
        self.vertexStrideData                   = dict()
        self.bone_matrix_bind_pose_data         = dict()
        self.bone_matrix_inverse_bind_pose_data = dict()
        self.bone_matrix_offset_data            = dict()
        self.bone_map                           = dict()
        self.bone_ids                           = dict()
        
        self.BlendWeightArray                   = []
        self.BlendIndexArray                    = []
        self.empties                            = []
        self.bone_names                         = []
        self.bone_parent                        = []
        self.vertexElements                     = []
        self.vertexStrideType                   = []
        self.vertexBuffer                       = []
        self.faceBuffer                         = []
        self.verts                              = []
        self.uvs                                = []
        self.faceUVs                            = []
        self.edges                              = []
        self.faces                              = []
        self.bones                              = []
        self.bone_location                      = []
        self.quats                              = []
        self.world_transforms                   = []
        
        self.modelName                          = ' '
        
        self.version                            = 0
        self.vertexStrideElementCount           = 0
        self.vertexStrideSize                   = 0
        self.numberBones                        = 0
        self.vertexCount                        = 0
        self.VertexArray                        = 0
        self.NormalArray                        = 0
        self.TangentArray                       = 0
        self.TextureCoordArray                  = 0
        
        self.hasTex                             = False
        self.has_armature                       = False
        
# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportSomeData.bl_idname, text="Text Import Operator")

def register():
    bpy.utils.register_class(ZomboidImport)
    bpy.types.INFO_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ZomboidImport)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
    
    # test call
    bpy.ops.zomboid.import_model('INVOKE_DEFAULT')