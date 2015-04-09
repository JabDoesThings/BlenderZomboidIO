# Author: Jab (or 40BlocksUnder) | Joshua Edwards
# Link for more info: http://theindiestone.com/forums/index.php/topic/12864-blender
# Imports models from Zomboid format.

import io,math,bmesh,bpy

from bpy import context
from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector, Euler, Quaternion, Matrix
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
from math import pi

class ZomboidImport(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    
    # important since its how bpy.ops.import_test.some_data is constructed
    bl_idname    = "zomboid.import_model"
    bl_label     = "Import a Zomboid Model"
    filename_ext = ".txt"
    filter_glob  = StringProperty(
            default="*.txt",
            options={'HIDDEN'},
            )
    
    load_model = BoolProperty(
        name="Load Model",
        description="Whether or not to import the model mesh.",
        default=True,
        )
    
    load_armature = BoolProperty(
        name="Load Armature",
        description="Whether or not to import the armature, if present.",
        default=True,
        )
    
    load_model_weights = BoolProperty(
        name="Load Bone Weights",
        description="Load Bone weights if PZ armature is detected. (RECOMENDED!)",
        default=True,
        )
    
    load_animations = BoolProperty(
        name="Load Animations (WIP!)",
        description="Whether or not to import animations. (Not done yet!)",
        default=False,
        )
    
    lock_model_on_armature_detection = BoolProperty(
        name="Lock Model Transforms If Armature Present",
        description="Whether or not to lock the model, if an armature is present.",
        default=True,
        )
        
    should_optimize_armature = BoolProperty(
        name="Optimize Armature (Biped Models)",
        description="Optimizes the imported Armature for animation purposes.",
        default=False,
        )
    

    # Get the current scene
    scene = context.scene

#####################################################################################
###                                                                               ###
###   File Interpretation methods                                                 ###
###                                                                               ###
#####################################################################################      

    def read_header(self,file):
        self.version                  = read_float(file)
        self.modelName                = read_line(file)
        self.amtname                  = self.modelName + "_armature"
        self.vertexStrideElementCount = read_int(file)
        self.vertexStrideSize         = read_int(file)


    # Vertex Stride Data:
    # (Int)     Offset
    # (String)  
    def read_stride_data(self,file):

        for x in range(0,self.vertexStrideElementCount):
            
            value = read_line(file)
            
            type = read_line(file)
            
            self.vertexStrideType.append(type)
            
            if type == "TextureCoordArray":
                self.hasTex = True
            elif type == "BlendWeightArray":
                self.has_vert_bone_data = True
            
            # Place it in the dictionary
            self.vertexStrideData[type] = value


    def read_vertex_buffer(self,file):
        for x in range(0,int(self.vertexCount)):
        
            elementArray = []
        
            for element in range(0,self.vertexStrideElementCount):
                                
                if self.vertexStrideType[element] == "VertexArray":
                    
                    line = read_line(file)
                    vs = line.split(', ')

                    self.verts.append(Vector((float(vs[0]), float(vs[1]), float(vs[2]))) * matrix_3_transform_y_positive)

                elif self.vertexStrideType[element] == "TextureCoordArray":
                    line = read_line(file)
                    vs = line.split(', ')

                    self.uvs.append(Vector((float(vs[0]),float(1) - float(vs[1]))))
                    
                elif self.vertexStrideType[element] == "BlendWeightArray":
                    self.read_vertex_weight_values(file)
                elif self.vertexStrideType[element] == "BlendIndexArray":
                    self.read_vertex_weight_indexes(file)
                else:
                    line = read_line(file)
    
    
    def read_vertex_weight_values(self,file):
        weights = read_line(file)
        split   = weights.split(", ")
        array   = []
        
        for s in split:
            array.append(float(s))
        
        self.BlendWeightArray.append(array)
    
    
    def read_vertex_weight_indexes(self,file):
        indexes = read_line(file)
        split   = indexes.split(", ")
        array   = []
        
        for s in split:
            array.append(int(s))
        
        self.BlendIndexArray.append(array)
    
                    
    def read_faces(self,file):
        for x in range(0,self.numberOfFaces):
            
            face         = read_line(file)    
            faceVerts    = face.split(", ")
            faceVerts[0] = int(faceVerts[0])
            faceVerts[1] = int(faceVerts[1])
            faceVerts[2] = int(faceVerts[2])
            
            if self.hasTex:
                self.faceUVs.append([self.uvs[faceVerts[0]],self.uvs[faceVerts[1]],self.uvs[faceVerts[2]]])
            
            self.faces.append([faceVerts[0], faceVerts[1], faceVerts[2]])
                                    
            self.faceBuffer.append(faceVerts)


    def read_bone_hierarchy(self,file):
        for index in range(0,self.numberBones):
            
            boneIndex               = read_int(file)
            boneParentIndex         = read_int(file)
            boneName                = read_line(file)
            self.bone_ids[boneName] = boneIndex
            
            # Append the name and the parent ID
            self.bone_names.append(boneName)
            self.bone_parent.append(boneParentIndex)

    # Bind Pose:
    # (Int)    Bone Index
    # (Matrix) Bind Matrix
    def read_bone_bind_pose_data(self,file):
        
        for index in range(0,self.numberBones):
            
            boneIndex   = read_int(file)
            bone_matrix = read_matrix(file)
            
            self.bone_matrix_bind_pose_data[index] = bone_matrix
            

    def read_bone_bind_inverse_pose_data(self,file):
        
        for index in range(0,self.numberBones):
        
            boneIndex      = read_int(file)
            matrix_inverse = read_matrix(file)
            
            self.bone_matrix_inverse_bind_pose_data[index] = matrix_inverse


    def read_bone_offset_data(self,file):
        
        for index in range(0,self.numberBones):
        
            boneIndex          = read_int(file)
            bone_offset_matrix = read_matrix(file)
            
            self.bone_matrix_offset_data[index] = bone_offset_matrix.transposed().copy() * matrix_4_transform_y_positive
    
    
    # Animations:
    # (String) Anim Name
    # (Float)  Duration in Seconds
    # (Int)    Number of Frames
    # -- Frame (Int)        Bone Index
    # -- Frame (String)     Bone Name
    # -- Frame (Float)      Time in Seconds
    # -- Frame (Vector3)    Translation
    # -- Frame (Quaternion) Rotation
    def read_animations(self,file):
        
        bone_count = len(self.bone_names)
        
        for animation_index in range(0,self.animation_count):
            animation_name        = read_line(file)
            animation_time        = read_float(file)
            animation_frame_count = read_int(file)
            
            print("Reading Animation: " + animation_name + "...")
            
            key_frames            = []
            frame                 = Frame(bone_count, self)
            current_index         = -1
            last_index            = -1
            first                 = False
            
            animation = Animation(animation_name,animation_time,animation_frame_count)
            self.animations.append(animation)
            
            for keyframe_index in range(0, animation_frame_count):
                 
                current_index     = read_int(file)
                    
                # If this is true, one true frame loop occured.
                if current_index < last_index:
                    
                    
                    for index, kf in enumerate(key_frames):
                        frame.bones.append(kf.bone_index)
                        frame.bone_names.append(kf.bone_name)
                        frame.times.append(kf.time)
                        
                        # frame.bone_mats[kf.bone_name] = kf.matrix
                        frame.bone_locs[kf.bone_name] = kf.loc
                        frame.bone_rots[kf.bone_name] = kf.rot
                    
                    frame.key_frames = key_frames
                    frame.calculate(self)
                    
                    
                    # Add the frame to the animation.
                    animation.frames.append(frame)
                    
                    # Create a new frame to work with before continuing.
                    key_frames = []
                    frame = Frame(bone_count, self)
                    
                last_index = current_index
                    
                bone_name  = read_line(file)
                frame_time = read_float(file)
                loc        = read_vector(file)     * matrix_3_transform_y_positive
                rot        = read_quaternion(file) 
                mat        = matrix_from_quaternion_position(rot,loc)
                
                # Create a new key frame.
                key_frame     = KeyFrame(current_index,bone_name,frame_time,mat)
                key_frame.loc = loc
                key_frame.rot = rot
                
                # Add the KeyFrame to the array to package later.
                key_frames.append(key_frame)
                
            
            for kf in key_frames:
                frame.bones.append(kf.bone_index)
                frame.bone_names.append(kf.bone_name)
                frame.times.append(kf.time)
                
                # frame.bone_mats[kf.bone_name] = kf.matrix
                frame.bone_locs[kf.bone_name] = kf.loc
                frame.bone_rots[kf.bone_name] = kf.rot

            frame.key_frames = key_frames
            frame.calculate(self)
            
            # Add the frame to the animation.
            animation.frames.append(frame)

#####################################################################################
###                                                                               ###
###   Blender Data Creation methods                                               ###
###                                                                               ###
#####################################################################################

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
            
            if self.lock_model_on_armature_detection:
                # Lock the mesh so the armature has complete control.
                obj.lock_location = obj.lock_rotation = obj.lock_scale = [True, True, True]
            # Grab the Object-representation of the armature.
            obj_armature      = bpy.data.objects[self.amtname]
            
            
            # Select the model Object in Blender
            bpy.ops.object.select_pattern(pattern=self.modelName)
            # Set the parent to the Armature.
            obj.parent = obj_armature
            obj.parent_type = 'ARMATURE'
            # Modify the Object with the Armature.
            modifier = bpy.ops.object.modifier_add(type='ARMATURE')
            # Return to Object mode.
            bpy.ops.object.mode_set(mode = 'OBJECT')
            
            # Create Vertex Groups here for each bone and set the Vertex accordingly.
            for bone in self.armature.bones:
                # New VertexGroup
                bpy.ops.object.vertex_group_add()
                
                # Get the active group.
                vertex_group      = obj.vertex_groups.active    
                vertex_group.name = bone.name
                
                # Get the original index of the Armature.
                bone_import_index = int(obj_armature[bone.name])
                
                # Offset of the vertex to know which Vert we are dealing with.
                offset_vert = 0
                
                for vertex in me.vertices:
                    # Grab the Vertex's weight data.
                    vertex_weight_ids = self.BlendIndexArray[offset_vert]
                    vertex_weights    = self.BlendWeightArray[offset_vert]
                    
                    # For each bone weight
                    offset = 0
                    for vert_weight_id in vertex_weight_ids:
                        # If this bone is the one currently being looked at, set the weight.
                        if vert_weight_id == bone_import_index:
                            verts = []
                            verts.append(vertex.index)
                            vertex_group.add(verts, vertex_weights[offset], 'REPLACE')
                        # Increment Bone Weight offset
                        offset += 1
                    # Increment Vertex offset
                    offset_vert += 1
        
        # Return to Edit Mode for optimization.
        bpy.ops.object.mode_set(mode = 'EDIT')

        # Optimize mesh
        bpy.ops.mesh.remove_doubles()
        bpy.ops.mesh.tris_convert_to_quads()
        
        # Return to Object mode to finish up.
        bpy.ops.object.mode_set(mode = 'OBJECT')


    def create_armature(self):
        # Try to clear all selections.
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
        except:
            ok = None
        
        self.armature           = bpy.data.armatures.new(self.amtname)
        ob                      = bpy.data.objects.new(self.amtname, self.armature)
        scn                     = bpy.context.scene
        scn.objects.link(ob)
        scn.objects.active      = ob
        ob.select               = True
        
        obj_armature            = bpy.data.objects[self.amtname]
        obj_armature.show_x_ray = True
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        ###
        ### Create the Root transformation manually to set up the parent inheritance.
        ###
        
        ##########################################################################
        #------------------------------------------------------------------------#
        # Create the Root transformation manually to set up parent inheritance.  #
        bone            = self.armature.edit_bones.new(self.bone_names[0])       #
        matrix_location = self.bone_matrix_offset_data[0]                        #
        mat             = Matrix.Identity(4)                                     #
        mat_world       = matrix_location * mat                                  #
                                                                                 #
        self.world_transforms.append(mat_world)                                  #
        self.bones.append(bone)                                                  #
        
                                                                                 #
        self.bone_location.append(mat_world.decompose()[0])
                                                                                 
        bone.matrix = mat_world                                                  #
        bone.tail   = Vector((bone.head[0], bone.head[1], bone.head[2] + 0.075)) #
        ##########################################################################
        
        # Set up each bone.
        for x in range(1, self.numberBones):
            
            bone = self.armature.edit_bones.new(self.bone_names[x])
            
            print("Creating Bone: " + bone.name + "...")
            
            if bone.name == "Bip01":
                bone.head = Vector((0,0.075,0))
                bone.tail = Vector((bone.head[0], bone.head[1] + 0.075, bone.head[2]))
                
            self.bones.append(bone)
            
            parent_index = self.bone_parent[x]
            parent_bone  = self.bones[parent_index]
            
            matrix_location = self.bone_matrix_offset_data[x]
            matrix_rotation = self.bone_matrix_inverse_bind_pose_data[x]
            mat_world       = matrix_location * self.bone_matrix_offset_data[parent_index].copy().inverted()
            mat             = matrix_location.inverted().copy()
            self.world_transforms.append(mat_world)
            self.bone_location.append(mat.decompose()[0])
            
            
            #####################################################################################
            #-----------------------------------------------------------------------------------#
            # TODO: Could improve this by using the bind-pose rotation to create the rest pose. #
            #       Might have to do this later.                                                #
            print("Quaternion: " + str(matrix_rotation.decompose()[1]))
            
            bone.head = mat.decompose()[0]                                                      #
            bone.tail = Vector((bone.head[0], bone.head[1], bone.head[2] + 0.075))               #
                                                                                                #
            if parent_index != -1:                                                              #
                if bone.tail[0] == 0 and bone.tail[1] == 0 and bone.tail[2] == 0:               #
                    bone.tail = Vector((bone.head[0], bone.head[1], bone.head[2] + 0.075))       #
            else:                                                                               #
                bone.tail = Vector((bone.head[0], bone.head[1], bone.head[2] + 0.075))           #
            #####################################################################################
            
            bone.parent = parent_bone
        
        # TODO: Add a option to not load animations and optimize the armature for personal animation use.    
        if self.should_optimize_armature:
            self.optimize_armature()
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        obj_armature["ZOMBOID_ARMATURE"] = 1
        
        for x in range(0, self.numberBones):
            id   = x
            name = self.bone_names[id]
            bpy.ops.wm.properties_add(data_path="object.data")
            obj_armature[name] = id
            
    
    def optimize_armature(self):
        for x in range(1, self.numberBones):
          
            bone_name = self.bone_names[x]
            
            bone = self.armature.edit_bones[bone_name]
            bone_tail = bone.tail
          
            try:
                if self.amtname == "bob_armature":
                    if "Neck" in bone_name:
                        bone.tail = bone.children[2].head
                        continue
                    #if "Bip01" == bone_name:
                        #bone.tail = bone.children[0].head
                        

                if bone.children != None:
                    if bone.children[0] != None:
                        bone.tail = bone.children[0].head
            except:
                bone.tail = bone_tail
            
            if bone.tail[0] == 0 and bone.tail[1] == 0 and bone.tail[2] == 0:      
                bone.tail = Vector((bone.head[0], bone.head[1], bone.head[2] + 0.075))
            
            if "Nub" in bone.name:
                if bone.parent != None:
                    bone.head = bone.parent.tail
                else:
                    bone.head = self.bone_matrix_offset_data[x].inverted().copy().decompose()[0]
                
                bone.tail = Vector((bone.head[0], bone.head[1], bone.head[2] + 0.075))
            
            if "Foot" in bone.name:
                bone.tail = Vector((bone.head[0], bone.head[1], bone.head[2] - 0.075))
                
            if bone.parent != None:
                if bone.parent.tail == bone.head:
                    bone.use_connect = True
            
        for x in range(1, self.numberBones):
          
            bone_name = self.bone_names[x]
            bone = self.armature.edit_bones[bone_name]
            
            #if "Pelvis" in bone.name:
            #    new_parent = bone.children[0]
            #    bone.use_connect = False
            #    new_parent.parent = None
            #    bpy.ops.armature.select_all(action='DESELECT')
            #    bone.select = True
            #    bone.parent = new_parent
            #    break
            
        for x in range(0, self.numberBones):
            bone_name = self.bone_names[x]
            bone = self.armature.edit_bones[bone_name]
            
            if bone.tail == bone.head:
                print(bone.name)
                bone.tail = Vector((bone.head[0], bone.head[1], bone.head[2] + 0.075))
        
        bpy.ops.armature.select_all(action='SELECT')
        bpy.ops.armature.calculate_roll(type='GLOBAL_Z')
        
        bpy.ops.armature.select_all(action='DESELECT')
    
    
    def apply_pose(self):
        ok = None
        
    
    # WIP METHOD!!! This method will almost surely change, as this is the "I don't know what the hell I'm
    #     supposed to be doing" phase. 
    def create_animations(self):
        
        self.armature.show_axes = True
        
        # Set ourselves into the pose mode of the armature with nothing selected.
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.object.select_pattern(pattern=self.amtname)
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')
        
        frame_offset = 0
        
        
        # Go through each Animation.
        for animation in self.animations:
            
            if animation.name != "Run":
                continue
            
            # Create a new Action for the Animation.
            action = bpy.data.actions.new(name=animation.name)
            
            print("Rendering Animation: " + animation.name + "...")
            
            frame_offset = 0
            
            bone_animation_count = dict()
            
            for frame_index, frame in enumerate(animation.frames):
                for bone_name in frame.bone_names:
                    if frame_index == 0:
                        bone_animation_count[bone_name] = 0
                    else:
                        bone_animation_count[bone_name] += 1
                    
            # Loop through each frame.
            for frame in animation.frames:
                
                bone_parent_rot = dict()
                bone_transform = dict()

                #bone_transform['Root'] = frame.bone_rots['Root']
                
                for bone_name in self.bone_names:
                    bone_transform[bone_name] = Quaternion((1.0, 0.0, 0.0, 0.0))
                
                for bone_name in frame.bone_names:
                    if bone_animation_count[bone_name] == 0:
                        continue

                    if bone_name == 'Root':# or bone.parent.name == 'Root':
                        continue
                    
                    par = self.bone_names[self.bone_parent[self.bone_ids[bone_name]]]                    
                    print("par:" + str(par))
                    
                   
                    
                    try:
                        bone_transform[bone_name] = frame.bone_rots[bone_name].copy() * bone_transform[par].copy()
                    except:
                        ok = True
                
                p_bones = []
                #print("\n\nFrame: " + str(frame_offset))                
                # Bone offset to track which in the frame arrays is being accessed.
                bone_offset = 0 
                
                # Set the current frame in the scene to the offset.
                bpy.data.scenes[0].frame_current = frame_offset
                
                for bone_name in frame.bone_names:

                    # Grab the bone responsible for this action
                    bone = bpy.data.objects[self.amtname].pose.bones[bone_name]

                    if bone_animation_count[bone_name] == 0:
                        continue

                    if bone_name == 'Root':
                        continue

                    # Store it in the array to bind keyframe.
                    p_bones.append(bone)
                    
                    bone.rotation_mode == 'QUATERNION'
                    
                    bone_id   = self.bone_ids[bone.name]
                    parent_id = self.bone_parent[bone_id]

                    k_loc = frame.bone_locs[bone_name]
                    k_rot = frame.bone_rots[bone_name]
                    #k_rot = bone_transform[bone_name]
                    
                    bind_matrix   = self.bone_matrix_bind_pose_data[self.bone_ids[bone_name]].copy()
                    bind_matrix.transpose()
                    bind_rotation = bind_matrix.decompose()[1]
                    #bind_rotation = bone_transform[bone_name]
                    
                    
                    #k_matrix = k_rot.to_matrix().copy().to_4x4().copy()
#                    k_matrix = Matrix((
#                    [        1,        0,        0, k_rot[1]],
#                    [        0,        1,        0, k_rot[2]],
#                    [        0,        0,        1, k_rot[3]],
#                    [ k_rot[1], k_rot[2], k_rot[3], k_rot[0]]))
#                    
#                   
#                    k_matrix = k_matrix.copy().transposed() * matrix_4_transform_y_positive
#                    print(k_matrix)
                    #k_rot2 = k_matrix.copy().decompose()[1]

                    quat_b = Quaternion((0.0, 0.0, 1.0), math.radians(90.0))
                    #rotation = bind_rotation.rotation_difference(k_rot.copy().inverted())
                    #rotation = k_rot #* bind_rotation 
                    
                    rotation = bone_transform[bone_name]
                    
                    rotation = rotation.copy().inverted() #* quat_b.copy()
                    
                    
                    
                    w = rotation[0]
                    x = rotation[1]
                    y = rotation[2]
                    z = rotation[3]
                    
                    rotation.w =  w
                    rotation.x =  x
                    rotation.y = -z
                    rotation.z = -y
                    
                    #rotation.invert()
                    
                    axis_angle = rotation.to_axis_angle()
                    
                    _axis = axis_angle[0]
                    
                    angle = axis_angle[1]
                  
                    bpy.ops.object.select_pattern(pattern=bone_name)
                    bpy.ops.pose.rot_clear()
                    
                    #rotation.negate()
                    
                    
                    #bpy.ops.transform.rotate(value=angle,axis=(_axis[1], _axis[0], -_axis[2]), constraint_orientation='LOCAL')
                    
                    #rot_a = Quaternion()
                    #rot_a[1] = -rotation[2]
                    #rot_a[2] = -rotation[3]
                    #rot_a[3] = -rotation[0]
                    #rot_a[0] = rotation[1]
                    #bone.rotation_quaternion = rotation
                    
                    print(_axis)
                    
                    bpy.ops.transform.rotate(value=angle,axis=(_axis[0], _axis[1], _axis[2]), constraint_orientation='LOCAL')
                    #bpy.ops.transform.rotate(value=angle,axis=(_axis[1], _axis[2], _axis[0]))#, constraint_orientation='LOCAL')
                    
                    
                    #bpy.ops.transform.rotate(value=-angle,axis=(_axis[1], _axis[2], _axis[0]))#, constraint_orientation='LOCAL')
                    
                    
                    #bpy.ops.transform.rotate(value=angle,axis=(       0, -_axis[0],        0), constraint_orientation='LOCAL')
                    #bpy.ops.transform.rotate(value=angle,axis=(       0,         0, _axis[2]), constraint_orientation='LOCAL')
                    
                    #Euler
                    
                    bpy.ops.pose.select_all(action='DESELECT')
                    
                    #if bone_name == "Bip01_R_Clavicle":
                        #print(bone_name)
                        #print("Quat Matrix: ")
                        #print(k_matrix)
                        #print("Result matrix")
                        #print(k_rot2)
                        #print(bone.rotation_quaternion)
                        #print()
                    #print("Bone: " + bone_name + " (" + str(bone_id) + ")")
                        
                    bpy.context.scene.update()
                    
                    # Increment the offset.
                    bone_offset += 1
                
                for bone in p_bones:
                    bpy.ops.object.select_pattern(pattern=bone.name)
                
                try:
                    # Create a Blender KeyFrame at this offset.
                    bpy.ops.anim.keyframe_insert_menu(type='Location')
                    
                    bpy.ops.anim.keyframe_insert_menu(type='Rotation')
                except:
                    ok = None
                    
                # De-select all bones to optimize the Blender KeyFrame.
                bpy.ops.pose.select_all(action='DESELECT')

                # Increment the offset.
                frame_offset += 1
            
            # For debug, we load one animation.
            break

        
    def execute(self, context):
        
        old_cursor = bpy.context.scene.cursor_location
        
        # Center the cursor.
        bpy.context.scene.cursor_location = (0.0, 0.0, 0.0)
        
        # The offset in the file read
        offset = 0

        with io.open(self.filepath, 'r') as file:
            end_of_file = False
            while file.readable() and end_of_file == False:
                    if offset == 0:
                        self.read_header(file)
                    elif offset == 1:
                        self.read_stride_data(file)
                    elif offset == 2:
                        self.vertexCount      = read_int(file)
                    elif offset == 3:
                        self.read_vertex_buffer(file)
                    elif offset == 4:
                        self.numberOfFaces    = read_int(file)
                    elif offset == 5:
                        self.read_faces(file)
                    elif offset == 6:
                        try:
                            self.numberBones  = read_int(file)
                            self.has_armature = True
                        except:
                            end_of_file       = True
                    elif offset == 7:
                        self.read_bone_hierarchy(file)
                    elif offset == 8:
                        self.read_bone_bind_pose_data(file)
                    elif offset == 9:
                        self.read_bone_bind_inverse_pose_data(file)
                    elif offset == 10:
                        self.read_bone_offset_data(file)
                    elif offset == 11:
                        if not self.load_animations:
                            end_of_file          = True
                        else:
                            try:
                                self.animation_count = read_int(file)
                                self.has_animations  = True
                            except:
                                end_of_file          = True
                    elif offset == 12:
                        self.read_animations(file)
                    offset+=1
                    if offset > 13 or end_of_file:
                        break
                    
            # Close the file.
            file.close()
        
        if self.has_armature and self.load_armature:
            # Create the Armature for proceeding animation data
            self.create_armature()
            
            
            #
            #self.apply_pose()
        
        if self.load_animations and self.has_animations:
            self.create_animations()
        
        # Check for meshes with Blend data and no armature.
        if self.has_armature == False and self.has_vert_bone_data == True and self.load_model_weights:
            
            valid_arm     = False
            armature_name = ''
            
            for armature in bpy.data.objects:
                try:
                    test = armature["ZOMBOID_ARMATURE"]
                    if test != -1:
                        armature_name = armature.name
                        self.armature = armature.data
                        self.amtname  = armature.name
                        self.has_armature = True
                        break
                except:
                    ok = True
            
            if valid_arm:
                obj_armature = bpy.data.objects[armature_name]
                for bone in obj_armature.data.bones:
                    bone_name = bone.name
                    id = self.bone_ids[bone_name] = obj_armature[bone_name]
                    self.bone_names[id] = bone_name
                    
        if self.load_model:
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
        
        
        self.animations                         = []
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
        self.animation_count                    = 0
        
        
        #self.load_armature                      = True
        self.hasTex                             = False
        self.has_armature                       = False
        self.has_animations                     = False
        self.has_vert_bone_data                 = False



class Animation:
    
    
    def __init__(self,name,time,frame_count):
        self.name                               = name
        self.time                               = time
        self.frame_count                        = frame_count
        self.key_frames                         = []
        self.frames                             = []
    


class Frame:


    def calculate(self, zomboid_import):
        self.update_bone_transforms(zomboid_import)
        self.update_world_transforms(zomboid_import)
        
        
    def update_bone_transforms(self, zomboid_import):
        for index, key_frame in enumerate(self.key_frames):
            
            bone_name = zomboid_import.bone_names[index]
            bone_transform = matrix_from_quaternion_position(key_frame.rot, key_frame.loc)
            
            self.bone_transforms[bone_name] = bone_transform
            self.bone_matrices_index[bone_name] = key_frame.bone_index
    
    
    def update_world_transforms(self, zomboid_import):
        identity = set_identity()
        temp_vec = Vector((0.0, 1.0, 0.0))
        identity = rotate(0.0, temp_vec, identity)
        self.world_transforms['Root'] = self.bone_transforms['Root'] * identity
        
        for bone_index in range(1, len(zomboid_import.bone_names)):
            bone_name         = zomboid_import.bone_names[bone_index]
            parent_bone_index = zomboid_import.bone_parent[bone_index]
            parent_name       = zomboid_import.bone_names[parent_bone_index]
            
            self.world_transforms[bone_name] = self.bone_transforms[bone_name] * self.world_transforms[parent_name]
            
            
    def update_skin_transforms(self, zomboid_import):
        
        bone_offsets = zomboid_import.bone_matrix_offset_data
        
        for bone_index in range(0, len(zomboid_import.bone_names)):
            
            bone_name = zomboid_import.bone_names[index]
            
            self.skin_transforms[bone_name] = bone_offsets[bone_name] * self.world_transforms[bone_name]
    
    
    
    def __init__(self, bone_count, zomboid_import):
        
        self.bone_matrices_index                = dict()
        self.bone_transforms                    = dict()
        self.world_transforms                   = dict()
        self.skin_transforms                    = dict()
        self.bone_matrices                      = dict()
        
        self.key_frames                         = []
        self.bones                              = []
        self.bone_names                         = []
        self.times                              = []    
        self.bone_mats                          = []
        self.bone_locs                          = dict()
        self.bone_rots                          = dict()
        
        for bone_name in zomboid_import.bone_names:
            self.bone_transforms[bone_name]  = set_identity()
            self.world_transforms[bone_name] = set_identity()
            self.skin_transforms[bone_name]  = set_identity()
        
        
class KeyFrame:
    
    
    def __init__(self,bone_index,bone_name,frame_time,mat):
        self.bone_index                         = bone_index
        self.bone_name                          = bone_name
        self.time                               = frame_time
        self.matrix                             = mat
        self.loc                                = Vector((0,0,0))
        self.rot                                = Quaternion()


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
    
#####################################################################################
###                                                                               ###
###   File I/O methods                                                            ###
###                                                                               ###
#####################################################################################                   
          
def read_line(file):
    string = '#'
    while string.startswith("#"):
        string = str(file.readline().strip())
    return string
  
                  
def read_int(file):
    return int(read_line(file))


def read_float(file):
    return float(read_line(file))


def read_vector(file):
    line = read_line(file)
    split = line.split(", ")
    return Vector((float(split[0]), float(split[1]), float(split[2])))


def read_quaternion(file):
    line = read_line(file)
    split = line.split(", ")
    q = Quaternion()
    
    x = float(split[0])
    y = float(split[1])
    z = float(split[2])
    w = float(split[3])

    q[0] = w
    q[1] = x
    q[2] = y
    q[3] = z
    
    return q


def read_matrix(file):
    s1 = read_line(file).split(", ")
    s2 = read_line(file).split(", ")
    s3 = read_line(file).split(", ")
    s4 = read_line(file).split(", ")
    
    m00 = float(s1[0])
    m01 = float(s1[1])
    m02 = float(s1[2])
    m03 = float(s1[3])
    m04 = float(s2[0])
    m05 = float(s2[1])
    m06 = float(s2[2])
    m07 = float(s2[3])
    m08 = float(s3[0])
    m09 = float(s3[1])
    m10 = float(s3[2])
    m11 = float(s3[3])
    m12 = float(s4[0])
    m13 = float(s4[1])
    m14 = float(s4[2])
    m15 = float(s4[3])

#    m = Matrix(
#        ([m00, m01, m02, m03],
#        [m04, m05, m06, m07],
#        [m08, m09, m10, m11],
#        [m12, m13, m14, m15]))
#    return m

    m = Matrix(
        ([m00, m04, m08, m12],
         [m01, m05, m09, m13],
         [m02, m06, m10, m14],
         [m03, m07, m11, m15]))
    return m


def quat_equals(q1,q2):
    return q1.w == q2.w and q1.x == q2.x and q1.y == q2.y and q1.z == q2.z


quat_transform_y_positive = Euler((pi/2, 0, 0),"XYZ").to_quaternion()


matrix_3_transform_y_positive = Matrix((( 1, 0, 0 )   ,( 0, 0, 1 )   ,( 0,-1, 0 )                  ))
matrix_4_transform_y_positive = Matrix((( 1, 0, 0, 0 ),( 0, 0, 1, 0 ),( 0,-1, 0, 0 ),( 0, 0, 0, 1 )))


matrix_3_transform_z_positive = Matrix((( 1, 0, 0 )   ,( 0, 0,-1 )   ,( 0, 1, 0 )                  ))
matrix_4_transform_z_positive = Matrix((( 1, 0, 0, 0 ),( 0, 0,-1, 0 ),( 0, 1, 0, 0 ),( 0, 0, 0, 1 )))