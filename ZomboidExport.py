import io, math, bmesh, bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
from mathutils import Vector, Euler, Quaternion, Matrix


class ZomboidExport(Operator, ExportHelper):
    bl_idname = "zomboid.export_model"
    bl_label = "Export a Zomboid Model"
    filename_ext = ".txt"

    filter_glob = StringProperty(
            default="*.txt",
            options={'HIDDEN'},
            )

    use_setting = BoolProperty(
            name="Example Boolean",
            description="Example Tooltip",
            default=True,
            )

    type = EnumProperty(
            name="Example Enum",
            description="Choose between two items",
            items=(('OPT_A', "First Option", "Description one"),
                   ('OPT_B', "Second Option", "Description two")),
            default='OPT_A',
            )
    
    
    def prepare_mesh(self):
        
        self.object_original = bpy.context.active_object
        # Grab the name of the selected object
        self.mesh_name = self.object_original.name
        
        # Duplicate the object to modify without affecting the actual model
        bpy.ops.object.duplicate()
        
        object = self.object = bpy.context.active_object
        mesh   = self.mesh   = object.data

        # We need to be in edit-mode to fix up the duplicate
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        bpy.ops.mesh.select_all(action='SELECT')
        
        # In order to be a valid format, the mesh needs to be
        #    in triangulated.
        bpy.ops.mesh.quads_convert_to_tris()
        
        # Go back to Object mode to apply polygon modifications.
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.object.mode_set(mode = 'OBJECT')
        # Grab the count of vertices.
        self.mesh_vertex_count = len(object.data.vertices)
        
        # Create a boolean for asking if the mesh has uv map data 
        has_uv_mapping = self.mesh_has_uv_mapping = len(mesh.uv_textures) > 0
        
        # Assign UV Map data if it exists.
        if has_uv_mapping:
            self.vertex_stride_element_count += 1
            self.uv_texture = mesh.uv_textures.active.data[:]
            self.uv_layer   = mesh.uv_layers.active.data[:]
            
        # Calculate face normals
        mesh.calc_normals_split()
        
        self.mesh_loops = mesh.loops
        
        
        
    def process_mesh(self):
        
        self.global_matrix = Matrix()
        self.mesh_matrix   = self.object.matrix_world

        object      = self.object
        mesh        = self.mesh
        mesh_matrix = self.mesh_matrix

        mesh.update(calc_tessface=True)
        
        #for v in range(0, len(mesh.vertices)):
        #    vert = mesh.vertices[v]
        #    self.verts[v] = Vertex()
        #    self.verts[v].id = v
        #    self.verts[v].co = vert.co
        #    self.verts[v].normal = vert.normal
        
        #for tess in mesh.tessfaces:
        #    face = Face()
        #    face.id = tess.index
        #    offset = 0
        #    for v in tess.vertices:
        #        
        #        vert = mesh.vertices[v]
        #        
        #        face.verts.append(v)
        #    
        #        offset += 1
        #    
        #    self.faces.append(face)
        
        #bpy.ops.object.mode_set(mode = 'EDIT')
        
        for f in mesh.polygons:
            face = Face()
            face.id = f.index
            for i in f.loop_indices:
                l = mesh.loops[i]
                v = mesh.vertices[l.vertex_index]
                vert = Vertex()
                vert.id = l.vertex_index
                vert.co = v.co
                vert.normal = v.normal
                
                uvl = 0
                for j,ul in enumerate(mesh.uv_layers):
                    
                    if uvl > 0:
                        print("UV Layer: " + str(uvl))
                    #print("\t\tUV Map", j, "has coordinates", ul.data[l.index].uv, \
                    #    "for this loop index")
                    vert.texture_coord = ul.data[l.index].uv
                    
                    uvl += 1
                face.verts.append(vert)
            self.faces.append(face)
        
        verts      = []
        has_vert   = dict()
        vert_index = dict()
        
        vert_offset = 0
        for f in self.faces:
            for index in range(0,len(face.verts)):
                print(index)
                f_v = f.verts[index]
                key = str(f_v.co) + " " + str(f_v.texture_coord)
                print(key)
                try:
                    has_v = has_vert[key]
                    if has_v:
                        f.vert_ids.append(vert_index[key])
                    else:
                        has_vert[key]   = True
                        f.verts[index]  = f_v
                        f_v.id          = vert_offset
                        vert_index[key] = vert_offset
                        f.vert_ids.append(vert_offset)
                        verts.append(f_v)
                        vert_offset    += 1
                        
                except:
                    has_vert[key]   = True
                    f.verts[index]  = f_v
                    f_v.id          = vert_offset
                    vert_index[key] = vert_offset
                    f.vert_ids.append(vert_offset)
                    verts.append(f_v)
                    vert_offset    += 1
            
            #del f.verts
        
        #del has_vert
        #del vert_index
        
        self.verts = verts
        
        #bpy.ops.object.mode_set(mode = 'OBJECT')
                    
    def write_header(self, file):
        write_comment(file, "Project Zomboid Skinned Mesh")
        
        write_comment(file, "File Version:")
        write_line(file, 1.0)
        
        write_comment(file, "Model Name:")
        write_line(file, self.mesh_name)
        
        
    def write_vertex_buffer(self, file):
        
        write_comment(file, "Vertex Stride Element Count:")
        write_line(file, self.vertex_stride_element_count)
        
        # This seems to be 76 in all files.
        write_comment(file, "Vertex Stride Size (in bytes):")
        write_line(file, 76)
        
        write_comment(file, "Vertex Stride Data:")
        write_comment(file, "(Int)    Offset"    )
        write_comment(file, "(String) Type"      )
        
        offset = 0
        if self.mesh_has_vertex_array:
            write_line(file, offset                          )
            write_line(file, self.vertex_array_name          )
            offset += self.offset_vertex_array
        if self.mesh_has_normal_array:
            write_line(file, offset                          )
            write_line(file, self.normal_array_name          )
            offset += self.offset_normal_array
        if self.mesh_has_tangent_array:
            write_line(file, offset                          )
            write_line(file, self.tangent_array_name         )
            offset += self.offset_tangent_array
        if self.mesh_has_uv_mapping:
            write_line(file, offset                          )
            write_line(file, self.texture_coord_array_name   )
            offset += self.offset_texture_coord_array
        if self.mesh_has_bone_weights:
            write_line(file, offset  )
            write_line(file, self.blend_weight_array_name    )
            offset += self.offset_blend_weight_array
            write_line(file, offset )
            write_line(file, self.blend_index_array_name     )
            offset += self.offset_blend_index_array
        
        del offset
        
        write_comment(file, "Vertex Count:")
        write_line(file, len(self.verts))
        
        write_comment(file, "Vertex Buffer:")
        for vert in self.verts:
            #vert = self.verts[key]
            if self.mesh_has_vertex_array:
                write_vector_3(file, vert.co)
            if self.mesh_has_normal_array:
                write_vector_3(file, vert.normal)
            if self.mesh_has_tangent_array:
                write_vector_3(file, vert.tangent)
            if self.mesh_has_uv_mapping:
                write_uv(file, vert.texture_coord)
            #if self.mesh_has_bone_weights:
                
        
    def write_faces(self, file):
        
        write_comment(file, "Number of Faces:")
        write_line(file, len(self.faces))
        
        write_comment(file, "Face Data:")
        for face in self.faces:
            write_face(file, face)
    
    def execute(self, context):
        
        try:
            bpy.ops.object.mode_set(mode = 'OBJECT')
        except:
            ok = None
        
        object = self.object = bpy.context.active_object
        
        # Checks to see if selection is avaliable AND a Mesh.
        if object == None:
            print("No Mesh selected.")
            return {'FINISHED'}
        if object.type != 'MESH':
            print("Object selected is not a mesh: " + str(object.type))
            return {'FINISHED'}
        
        
        self.prepare_mesh()
        
        self.process_mesh()
        
        with io.open(self.filepath, 'w') as file:
            self.write_header(file)
            self.write_vertex_buffer(file)
            self.write_faces(file)
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        # If the object active is not the original, delete it.
        if bpy.context.active_object.name != self.mesh_name:
            bpy.ops.object.delete()
        
        # Reset the object selection.
        bpy.ops.object.select_pattern(pattern=self.mesh_name)
        context.scene.objects.active = self.object_original
        self.object_original = True
        
        return {'FINISHED'}

    def __init__(self):
        self.verts                              = []
        self.faces                              = []
        
        self.global_matrix                      = None
        
        self.object_original                    = None
        self.object                             = None
        self.mesh                               = None
        self.mesh_name                          = "Untitled_Mesh"
        self.mesh_matrix                        = None
        self.mesh_loops                         = None
        
        self.vertex_array_name                  = 'VertexArray'
        self.normal_array_name                  = 'NormalArray'
        self.tangent_array_name                 = 'TangentArray'
        self.texture_coord_array_name           = 'TextureCoordArray'
        self.blend_weight_array_name            = 'BlendWeightArray'
        self.blend_index_array_name             = 'BlendIndexArray'
        
        self.mesh_vertex_count                  = 0
        
        self.offset_vertex_array                = 12
        self.offset_normal_array                = 12
        self.offset_tangent_array               = 12
        self.offset_texture_coord_array         = 8
        self.offset_blend_weight_array          = 16
        self.offset_blend_index_array           = 0
        
        self.vertex_stride_element_count        = 2
        self.mesh_has_vertex_array              = True
        self.mesh_has_normal_array              = True
        self.mesh_has_tangent_array             = False
        self.mesh_has_uv_mapping                = False
        self.mesh_has_bone_weights              = False


class Vertex:
    
    def __init__(self):
        self.mesh_vertex                        = None
        self.polygon                            = None
        
        self.co                                 = Vector((0.0,0.0,0.0))
        self.normal                             = Vector((0.0,0.0,0.0))
        self.tangent                            = Vector((0.0,0.0,0.0))
        self.texture_coord                      = Vector((0.0,0.0))
        
        self.blend_weight                       = []
        self.blend_index                        = []
        
        self.id                                 = -1
    
    
class Face:
    
    def __init__(self):
        self.vert_ids                           = []
        self.verts                              = []
        self.id                                 = -1
        
        
        
def menu_func_export(self, context):
    self.layout.operator(ZomboidExport.bl_idname, text="Text Export Operator")

def register():
    bpy.utils.register_class(ZomboidExport)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ZomboidExport)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
    bpy.ops.zomboid.export_model('INVOKE_DEFAULT')

#####################################################################################
###                                                                               ###
###   File I/O methods                                                            ###
###                                                                               ###
#####################################################################################         


# Writes a line to the file.
def write_line(file, line, new_line=True):
    
    # Converts any arbitrary primitives into a String just in-case.
    finished_line = str(line)
    
    # If new_line is true, add a newline marker at the end.
    if new_line:
        finished_line = finished_line + "\n"
    
    # Write the line to a file.
    file.write(finished_line)
    
def write(file, line):
    write_line(file, line, new_line=False)
    
# Writes a comment to the file.
def write_comment(file, comment):
    
    final_comment = "# " + str(comment)
    
    write_line(file, final_comment)
    
    
def write_vector_3(file, vector):
    string = str(round(vector[0], 8)) + ", " + str(round(vector[1], 8)) + ", " + str(round(vector[2], 8))
    write_line(file, string)
    

def write_uv(file, vector):
    #print("Vec2: " + str(vector))
    string = str(vector[0]) + ", " + str(1.0 - vector[1])
    write_line(file, string)
    
    
def write_array(file, array):
    string = ""
    
    for element in array:
        string += str(element) + ", "
    
    write_line(file, string[:-2])
    
def write_face(file, face):
    string = ""
    for index in face.vert_ids:
        string += str(index) + ", "
    
    write_line(file, string[:-2])
    
#####################################################################################
###                                                                               ###
###   Math Methods                                                                ###
###                                                                               ###
##################################################################################### 