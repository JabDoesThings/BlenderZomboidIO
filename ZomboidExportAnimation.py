# Author: Jab (or 40BlocksUnder) | Joshua Edwards
# Link for more info: http://theindiestone.com/forums/index.php/topic/12864-blender
# Exports models to Zomboid format.

import io, math, bmesh, bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from bpy.types import Operator
from mathutils import Vector, Euler, Quaternion, Matrix


class ZomboidExportAnimation(Operator, ExportHelper):
    bl_idname    = "zomboid.export_animation"
    bl_label     = "Export a Zomboid Animation"
    filename_ext = ".pza"
    filter_glob  = StringProperty(
            default="*.pza",
            options={'HIDDEN'},
            )

    animation_time = FloatProperty(
            name="Animation Speed",
            description="How fast the animation runs in-game.",
            default=1.0,
            )
    
    # REVERSE THESE STEPS:
    # 1) Turn the translation and rotation into a Frame Matrix
    # 2) Create a World Matrix by multiplying the Parent World Matrix with the Frame Matrix
    # 3) Create the Product Matrix by multiplying the World Matrix with the Bone Matrix
    def prepare(self):
        bpy.ops.object.mode_set(mode = 'POSE')
        
        # Grab the start, end, and range for the frames in the action.
        self.frame_first = get_first_frame(self.action)
        self.frame_last = get_last_frame(self.action)
        self.frame_count = get_frame_count(self.action)
        # Create Animation object.
        self.animation = Animation(self.action.name)
        
        for index in range(self.frame_first, self.frame_last):
            # Sets the world to this frame.
            set_frame(index)
            # Create Frame Object
            frame = Frame(index)
            
            for b in self.object.pose.bones:
                bone = Bone(b.name, self.object[b.name])
                
                bip_offset = b.bone.matrix_local.copy()
                bip_offset_inv = bip_offset.copy().inverted()
#               print('Offset Matrix: ')
#               print(to_lwjgl_matrix(bip_offset_inv))
                bip_basis = b.matrix_basis
                
                t1 = bip_basis * bip_offset_inv
                
                loc1 = (bip_offset).decompose()[0]
                loc2 = (bip_basis.copy()).decompose()[0]
                
                loc = Vector((loc1[0] - loc2[2], loc1[1] + loc2[1], loc1[2] - loc2[0]))
                rot = t1.decompose()[1]
                
                bone.loc = loc
                bone.rot = rot
                
                frame.bones.append(bone)
            
            frame.organize_bones()
            # Add the Frame to the Animation
            self.animation.frames.append(frame)
        
        
    def write(self):
        with io.open(self.filepath, 'w') as file:
            write_line(file, '#Animation Name')
            write_line(file, self.action.name)
            write_line(file, '#Animation Time')
            write_line(file, efloat(self.animation_time * (self.frame_count / 30)))
            write_line(file, '#Animation Frame Count')
            write_line(file, str(self.frame_count))
            write_line(file, '# Start of Frame Data')
            # Frame Data
            for frame in self.animation.frames:
                for bone in frame.bones:
                    write_line(file, str(bone.id))
                    write_line(file, bone.name)
                    # NOTE: 3DS at the time of exporting the 
                    #     vanilla models is 30 frames per second. 
                    write_line(file, efloat((((frame.id - self.frame_first)) / 30) * self.animation_time))
                    write_vec3(file, bone.loc)
                    write_quat(file, bone.rot) 
            
    def execute(self, context):
        try:
            bpy.ops.object.mode_set(mode = 'OBJECT')
        except:
            ok = None
        armature = self.object = bpy.context.active_object
        # Checks to see if selection is avaliable AND a Mesh.
        if armature == None:
            print("No armature selected.")
            return {'FINISHED'}
        if armature.type != 'ARMATURE':
            print("Object selected is not a armature: " + str(armature.type))
            return {'FINISHED'}
        self.armature = armature
        self.object = bpy.data.objects[armature.name]
        self.action = self.object.animation_data.action
        self.prepare()
        self.write()
        return {'FINISHED'}

    def __init__(self):
        # Object for the Armature
        self.object = None
        # Armature to export.
        self.armature = None
        # Action with animation
        self.action = None
        # Animation Object
        self.animation = None


class Animation:
    
    def __init__(self, name):
        self.name   = name
        self.frames = [ ]
        
        
class Frame:
    
    def __init__(self, id):
        self.id = id
        self.bones = [ ]
        
    def organize_bones(self):
        
        # Lowest ID number
        low = 65535
        # Highest ID number
        high = 0
        
        for bone in self.bones:
            id = bone.id
            if id < low:
                low = id
            if id > high:
                high = id
        
        new_bones = [ ]
        for index in range(low, high):
            for bone in self.bones:
                if bone.id is index:
                    new_bones.append(bone)
                    break
        self.bones = new_bones
                

class Bone:
    
    def __init__(self, name, id):
        self.name  = name
        self.rot   = None
        self.loc   = None
        self.scale = None
        self.id    = id
        

def menu_func_export(self, context):
    self.layout.operator(ZomboidExportAnimation.bl_idname, text="Text Export Operator")

def register():
    bpy.utils.register_class(ZomboidExportAnimation)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ZomboidExportAnimation)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
    bpy.ops.zomboid.export_animation('INVOKE_DEFAULT')


def get_last_frame(action):
    return int(round(action.frame_range[1]))

def get_first_frame(action):
    return int(round(action.frame_range[0]))

def get_frame_count(action):
    return get_last_frame(action) - get_first_frame(action) + 1
    
def set_frame(frame):
    bpy.context.scene.frame_current = int(round(frame))

def efloat(float):
    return "%0.8f" % float

class Matrix4f():
    
    def __init__(self):
        self.m00 = 1.0
        self.m01 = 0.0
        self.m02 = 0.0
        self.m03 = 0.0
        self.m10 = 0.0
        self.m11 = 1.0
        self.m12 = 0.0
        self.m13 = 0.0
        self.m20 = 0.0
        self.m21 = 0.0
        self.m22 = 1.0
        self.m23 = 0.0
        self.m30 = 0.0
        self.m31 = 0.0
        self.m32 = 0.0
        self.m33 = 1.0
        
    def __str__(self):
        return 'M`atrix4f' + '\n[' + efloat(self.m00) + ', ' + efloat(self.m01) + ', ' + efloat(self.m02) + ', ' + efloat(self.m03) + '],\n[' + efloat(self.m10) + ', ' + efloat(self.m11) + ', ' + efloat(self.m12) + ', ' + efloat(self.m13) + '],\n[' + efloat(self.m20) + ', ' + efloat(self.m21) + ', ' + efloat(self.m22) + ', ' + efloat(self.m23) + '],\n[' + efloat(self.m30) + ', ' + efloat(self.m31) + ', ' + efloat(self.m32) + ', ' + efloat(self.m33) + ']'
        
    def set_identity(self):
        self.m00 = 1.0
        self.m01 = 0.0
        self.m02 = 0.0
        self.m03 = 0.0
        self.m10 = 0.0
        self.m11 = 1.0
        self.m12 = 0.0
        self.m13 = 0.0
        self.m20 = 0.0
        self.m21 = 0.0
        self.m22 = 1.0
        self.m23 = 0.0
        self.m30 = 0.0
        self.m31 = 0.0
        self.m32 = 0.0
        self.m33 = 1.0
        
    def copy(self):
        nm = Matrix4f()
        nm.m00 = self.m00
        nm.m01 = self.m01
        nm.m02 = self.m02
        nm.m03 = self.m03
        nm.m10 = self.m10
        nm.m11 = self.m11
        nm.m12 = self.m12
        nm.m13 = self.m13
        nm.m20 = self.m20
        nm.m21 = self.m21
        nm.m22 = self.m22
        nm.m23 = self.m23
        nm.m30 = self.m30
        nm.m31 = self.m31
        nm.m32 = self.m32
        nm.m33 = self.m33
        return nm
    
    def to_blender_matrix(self):
        m = Matrix(
         ([self.m00, self.m10, self.m20, self.m30],
          [self.m01, self.m11, self.m21, self.m31],
          [self.m02, self.m12, self.m22, self.m32],
          [self.m03, self.m13, self.m23, self.m33]))
        return m.transposed()
    
def to_lwjgl_matrix(self, blender_matrix):
    m = Matrix4f()
    b = blender_matrix.copy().transposed()
    m.m00 = b[0][0]
    m.m01 = b[1][0]
    m.m02 = b[2][0]
    m.m03 = b[3][0]
    m.m10 = b[0][1]
    m.m11 = b[1][1]
    m.m12 = b[2][1]
    m.m13 = b[3][1]
    m.m20 = b[0][2]
    m.m21 = b[1][2]
    m.m22 = b[2][2]
    m.m23 = b[3][2]
    m.m30 = b[0][3]
    m.m31 = b[1][3]
    m.m32 = b[2][3]
    m.m33 = b[3][3]
    return m

def translate(vec, src, dest):
    if dest == None:
        dest = Matrix4f()
    
    dest.m30 += src.m00 * vec.x + src.m10 * vec.y + src.m20 * vec.z
    dest.m31 += src.m01 * vec.x + src.m11 * vec.y + src.m21 * vec.z
    dest.m32 += src.m02 * vec.x + src.m12 * vec.y + src.m22 * vec.z
    dest.m33 += src.m03 * vec.x + src.m13 * vec.y + src.m23 * vec.z
    
    return dest

def mul(left,right,dest):
    if dest == None:
        dest = Matrix4f()
    
    m00 = left.m00 * right.m00 + left.m10 * right.m01 + left.m20 * right.m02 + left.m30 * right.m03
    m01 = left.m01 * right.m00 + left.m11 * right.m01 + left.m21 * right.m02 + left.m31 * right.m03
    m02 = left.m02 * right.m00 + left.m12 * right.m01 + left.m22 * right.m02 + left.m32 * right.m03
    m03 = left.m03 * right.m00 + left.m13 * right.m01 + left.m23 * right.m02 + left.m33 * right.m03
    m10 = left.m00 * right.m10 + left.m10 * right.m11 + left.m20 * right.m12 + left.m30 * right.m13
    m11 = left.m01 * right.m10 + left.m11 * right.m11 + left.m21 * right.m12 + left.m31 * right.m13
    m12 = left.m02 * right.m10 + left.m12 * right.m11 + left.m22 * right.m12 + left.m32 * right.m13
    m13 = left.m03 * right.m10 + left.m13 * right.m11 + left.m23 * right.m12 + left.m33 * right.m13
    m20 = left.m00 * right.m20 + left.m10 * right.m21 + left.m20 * right.m22 + left.m30 * right.m23
    m21 = left.m01 * right.m20 + left.m11 * right.m21 + left.m21 * right.m22 + left.m31 * right.m23
    m22 = left.m02 * right.m20 + left.m12 * right.m21 + left.m22 * right.m22 + left.m32 * right.m23
    m23 = left.m03 * right.m20 + left.m13 * right.m21 + left.m23 * right.m22 + left.m33 * right.m23
    m30 = left.m00 * right.m30 + left.m10 * right.m31 + left.m20 * right.m32 + left.m30 * right.m33
    m31 = left.m01 * right.m30 + left.m11 * right.m31 + left.m21 * right.m32 + left.m31 * right.m33
    m32 = left.m02 * right.m30 + left.m12 * right.m31 + left.m22 * right.m32 + left.m32 * right.m33
    m33 = left.m03 * right.m30 + left.m13 * right.m31 + left.m23 * right.m32 + left.m33 * right.m33
    dest.m00 = m00
    dest.m01 = m01
    dest.m02 = m02
    dest.m03 = m03
    dest.m10 = m10
    dest.m11 = m11
    dest.m12 = m12
    dest.m13 = m13
    dest.m20 = m20
    dest.m21 = m21
    dest.m22 = m22
    dest.m23 = m23
    dest.m30 = m30
    dest.m31 = m31
    dest.m32 = m32
    dest.m33 = m33
    
    return dest

def transpose(src, dest):
    if dest == None:
        dest = Matrix4f()
    
    m00 = src.m00
    m01 = src.m10
    m02 = src.m20
    m03 = src.m30
    m10 = src.m01
    m11 = src.m11
    m12 = src.m21
    m13 = src.m31
    m20 = src.m02
    m21 = src.m12
    m22 = src.m22
    m23 = src.m32
    m30 = src.m03
    m31 = src.m13
    m32 = src.m23
    m33 = src.m33
    dest.m00 = m00
    dest.m01 = m01
    dest.m02 = m02
    dest.m03 = m03
    dest.m10 = m10
    dest.m11 = m11
    dest.m12 = m12
    dest.m13 = m13
    dest.m20 = m20
    dest.m21 = m21
    dest.m22 = m22
    dest.m23 = m23
    dest.m30 = m30
    dest.m31 = m31
    dest.m32 = m32
    dest.m33 = m33
    
    return dest

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
    
    
def write_vec3(file, vector):
    string = efloat(round((vector[0]), 8)) + ", " + efloat(round((vector[1]), 8)) + ", " + efloat(round((vector[2]), 8))
    write_line(file, string)
    
def write_quat(file, q):
    string = efloat(round((q.x), 8)) + ", " + efloat(round((q.y), 8)) + ", " + efloat(round((q.z), 8)) + ", " + efloat(round((q.w), 8))
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
###   Helper Methods                                                              ###
###                                                                               ###
##################################################################################### 

class prettyfloat(float):
    def __repr__(self):
        return "%0.2f" % self

def get_bone_id_table(armature):
    arm = armature.data
    bone_names = [bone.name for bone in arm.bones]
    bone_ids   = dict()
    for bone_name in bone_names:
        try:
            bone_ids[bone_name] = int(armature[bone_name])
            print(bone_ids[bone_name])
        except:
            continue
    return bone_ids  

matrix_3_transform_z_positive = Matrix((( 1, 0, 0 )   ,( 0, 0,-1 )   ,( 0, 1, 0 )                  ))
matrix_4_transform_z_positive = Matrix((( 1, 0, 0, 0 ),( 0, 0,-1, 0 ),( 0, 1, 0, 0 ),( 0, 0, 0, 1 )))