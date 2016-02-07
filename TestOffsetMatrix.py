import bpy,math
from mathutils import Vector, Euler, Quaternion, Matrix

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
    
def to_lwjgl_matrix(blender_matrix):
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


def do_things():
    ok = None
    armature = bpy.data.armatures['bob_armature']
    object = bpy.data.objects['bob_armature']
    
    bip = object.pose.bones['Bip01']
    print('Bone name: Bip01')
    bip_offset = bip.bone.matrix_local.copy()
    bip_offset_inv = bip_offset.copy().inverted()
    print('Offset Matrix: ')
    print(to_lwjgl_matrix(bip_offset_inv))
    
    bip_basis = bip.matrix_basis
    
    t1 = bip_basis * bip_offset_inv
    rot = t1.decompose()[1]
    
    loc1 = (bip_offset).decompose()[0]
    loc2 = (bip_basis.copy()).decompose()[0]
    loc3 = Vector((loc1[0] - loc2[2], loc1[1] + loc2[1], loc1[2] - loc2[0]))
    print('\n')
    print('Bone offset:')
    print(loc3)
    print(rot)
    
   
    
do_things()