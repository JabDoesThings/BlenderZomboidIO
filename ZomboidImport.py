import bpy,io,bmesh
from bpy import context
from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector
from mathutils import Matrix
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

class ZomboidImport(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "zomboid.import_model"  # important since its how bpy.ops.import_test.some_data is constructed
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
        
                line = self.read_line(file)
        
                elementArray.append(line)
                
                if self.vertexStrideType[element] == "VertexArray":

                    vs = line.split(', ')

                    self.verts.append(Vector((float(vs[0]), float(vs[1]), float(vs[2]))))

                elif self.vertexStrideType[element] == "TextureCoordArray":

                    vs = line.split(', ')

                    self.uvs.append(Vector((float(vs[0]),float(1) - float(vs[1]))))
                    
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
            
            # Armature code. Will move.
            
            # bone = armature.edit_bones.new(boneName)
            # bone.length = 1
            # bone.tail = (0,0,1)
            # bones.append(bone)
            # if boneParentIndex >= 0:
            #     bone_parent = bones[boneParentIndex]
            #     bone.parent = bone_parent
            # else:
            #     bone.head = (0,0,1)
            #     bone.tail = (0,0,0)

            # print(boneName)
            # print("boneParentIndex: " + str(boneParentIndex))

    # Bind Pose:
    # (Int)    Bone Index
    # (Matrix) Bind Matrix
    def read_bone_bind_pose_data(self,file):
        
        for index in range(0,self.numberBones):
            
            boneIndex = self.read_int(file)
                        
            bone_matrix = self.read_matrix(file)
            
          
            # Armature code. Will move.
            # bone = self.bones[boneIndex]
            # bone.matrix = bone_matrix
            
            # Test code
            # if bone.parent != None:
            #     bone.tail = bone.parent.head
            #     bone.use_connect = True

    def read_bone_bind_inverse_pose_data(self,file):
        
        for index in range(0,self.numberBones):
        
            boneIndex = self.read_int(file)
        
            matrix_inverse = self.read_matrix(file)

            # Armature code. Will move.
            # bone = bones[boneIndex]

    def read_bone_offset_data(self,file):
        
        for index in range(0,self.numberBones):
        
            boneIndex = self.read_int(file)
            
            bone_offset_matrix = self.read_matrix(file)
            
            # Armature data. Will move.
            # bone = bones[boneIndex]
            # if bone.parent != None:
            #     bone.head = bone.parent.tail
            # bone.transform(bone_offset_matrix)

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

        # useful for development when the mesh may be invalid.
        # mesh.validate(verbose=True)
        bpy.ops.object.mode_set(mode = 'EDIT')

        bm = bmesh.from_edit_mesh(me)

        uv_layer = bm.loops.layers.uv.verify()
        bm.faces.layers.tex.verify()  # currently blender needs both layers.

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

        # Optimize mesh
        bpy.ops.mesh.remove_doubles()
        bpy.ops.mesh.tris_convert_to_quads()
        bpy.ops.object.mode_set(mode = 'OBJECT')

    def create_armature(self):
        # Clear selections and set to object mode.
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
        except:
            ok = None
        
        self.armature = bpy.data.armatures.new(amtname)
        
        self.object_armature = bpy.data.objects.new(amtname, armature)
        
        object_data_add(bpy.context, armature)
        
        bpy.ops.object.select_pattern(pattern=amtname)
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        #bone = armature.edit_bones.new('Bone')
        #bone.head = (0,0,0)
        #bone.tail = (0,0,1)

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

    def createObject(self, name, matrix):
        bpy.ops.object.empty_add(type="SPHERE")
        
    def execute(self, context):
    
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
        
        self.create_mesh()
        
        return {'FINISHED'}
        
    def __init__(self):
        self.vertexStrideData                   = dict()
        self.bone_matrix_bind_pose_data         = dict()
        self.bone_matrix_inverse_bind_pose_data = dict()
        self.bone_map                           = dict()
        self.bone_parent                        = dict()
        self.bone_matrix_offset_data            = dict()
        
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
        self.BlendWeightArray                   = 0
        self.BlendIndexArray                    = 0
        
        self.hasTex                             = False
        
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