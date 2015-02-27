import bpy,io,bmesh
from bpy import context
from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector
from mathutils import Matrix
from mathutils import Quaternion
from mathutils import Euler
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
            
            # Place it in the dictionary
            self.vertexStrideData[type] = value


    def read_vertex_buffer(self,file):
        for x in range(0,int(self.vertexCount)):
        
            elementArray = []
        
            for element in range(0,self.vertexStrideElementCount):
                                
                if self.vertexStrideType[element] == "VertexArray":
                    
                    line = read_line(file)
                    vs = line.split(', ')

                    self.verts.append(Vector((float(vs[0]), float(vs[1]), float(vs[2]))))

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
            
            self.bone_matrix_offset_data[index] = bone_offset_matrix
    
    
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
        
        for animation_index in range(0,self.animation_count):
            animation_name        = read_line(file)
            animation_time        = read_float(file)
            animation_frame_count = read_int(file)
            
            print("Reading Animation: " + animation_name + "...")
            
            key_frames            = []
            frame                 = Frame()
            current_index         = -1
            last_index            = -1
            first                 = False
            
            animation = Animation(animation_name,animation_time,animation_frame_count)
            self.animations.append(animation)
            
            for keyframe_index in range(0, animation_frame_count):
                
                current_index     = read_int(file)
                    
                # If this is true, one true frame loop occured.
                if current_index < last_index:
                    
                    for kf in key_frames:
                        frame.bones.append(kf.bone_index)
                        frame.bone_names.append(kf.bone_name)
                        frame.times.append(kf.time)
                        frame.bone_mats.append(kf.matrix)
                        frame.bone_locs.append(kf.loc)
                        frame.bone_rots.append(kf.rot)
                    
                    # Add the frame to the animation.
                    animation.frames.append(frame)
                    
                    # Create a new frame to work with before continuing.
                    key_frames = []
                    frame = Frame()
                    
                last_index = current_index
                    
                bone_name  = read_line(file)
                frame_time = read_float(file)
                loc        = read_vector(file)
                rot        = read_quaternion(file)#.inverted().copy()
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
                frame.bone_mats.append(kf.matrix)
                frame.bone_locs.append(kf.loc)
                frame.bone_rots.append(kf.rot)

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
                bone_import_index = self.bone_ids[bone.name]
                
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
        mat             = set_identity()                                         #
        mat_world       = matrix_location * mat                                  #
                                                                                 #
        self.world_transforms.append(mat_world)                                  #
        self.bones.append(bone)                                                  #
                                                                                 #
        bone.matrix = mat_world                                                  #
        bone.tail   = Vector((bone.head[0], bone.head[1] + 0.05, bone.head[2]))  #
        ##########################################################################
        
        # Set up each bone.
        for x in range(1, self.numberBones):
            
            bone = self.armature.edit_bones.new(self.bone_names[x])
            
            print("Creating Bone: " + bone.name + "...")
            
            if bone.name == "Bip01":
                bone.head = Vector((0,0.05,0))
                bone.tail = Vector((bone.head[0], bone.head[1] + 0.05, bone.head[2]))
                
            self.bones.append(bone)
            
            parent_index = self.bone_parent[x]
            parent_bone  = self.bones[parent_index]
            
            matrix_location = self.bone_matrix_offset_data[x]
            matrix_rotation = self.bone_matrix_inverse_bind_pose_data[x]
            mat_world       = matrix_location * self.bone_matrix_offset_data[parent_index].copy().inverted()
            mat             = matrix_location.inverted().copy()
            self.world_transforms.append(mat_world)

            #####################################################################################
            #-----------------------------------------------------------------------------------#
            # TODO: Could improve this by using the bind-pose rotation to create the rest pose. #
            #       Might have to do this later.                                                #
            bone.head = mat.decompose()[0]                                                      #
            bone.tail = Vector((bone.head[0], bone.head[1] + 0.05, bone.head[2]))               #
                                                                                                #
            if parent_index != -1:                                                              #
                if bone.tail[0] == 0 and bone.tail[1] == 0 and bone.tail[2] == 0:               #
                    bone.tail = Vector((bone.head[0], bone.head[1] + 0.05, bone.head[2]))       #
            else:                                                                               #
                bone.tail = Vector((bone.head[0], bone.head[1] + 0.05, bone.head[2]))           #
            #####################################################################################
            
            bone.parent = parent_bone
        
        # TODO: Add a option to not load animations and optimize the armature for personal animation use.    
        self.optimize_armature()
        
        bpy.ops.object.mode_set(mode='OBJECT')
    
    def optimize_armature(self):
        for x in range(1, self.numberBones):
          
            bone_name = self.bone_names[x]
            
            print("1st phase: " + bone_name)
            
            bone = self.armature.edit_bones[bone_name]
            bone_tail = bone.tail
          
            try:
                if self.amtname == "bob_armature":
                    if "Neck" in bone_name:
                        bone.tail = bone.children[2].head
                        continue
                    if "Bip01" == bone_name:
                        print("Bip01 exists")
                        bone.tail = bone.children[0].head

                if bone.children != None:
                    if bone.children[0] != None:
                        bone.tail = bone.children[0].head
            except:
                bone.tail = bone_tail
            
            if bone.tail[0] == 0 and bone.tail[1] == 0 and bone.tail[2] == 0:      
                bone.tail = Vector((bone.head[0], bone.head[1] + 0.05, bone.head[2]))
            
            if "Nub" in bone.name:
                if bone.parent != None:
                    bone.head = bone.parent.tail
                else:
                    bone.head = self.bone_matrix_offset_data[x].inverted().copy().decompose()[0]
                
                bone.tail = Vector((bone.head[0], bone.head[1] + 0.05, bone.head[2]))
            
            if "Foot" in bone.name:
                bone.tail = Vector((bone.head[0], bone.head[1] - 0.05, bone.head[2]))
                
            if bone.parent != None:
                if bone.parent.tail == bone.head:
                    bone.use_connect = True
            
        for x in range(1, self.numberBones):
          
            bone_name = self.bone_names[x]
            print("2nd phase: " + bone_name)  
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
            print("3rd phase: " + bone_name)
            bone = self.armature.edit_bones[bone_name]
            
            if bone.tail == bone.head:
                print(bone.name)
                bone.tail = Vector((bone.head[0], bone.head[1] + 0.05, bone.head[2]))
        
        bpy.ops.armature.select_all(action='SELECT')
        bpy.ops.armature.calculate_roll(type='GLOBAL_Z')
        
        bpy.ops.armature.select_all(action='DESELECT')
    
    
    # WIP METHOD!!! This method will almost surely change, as this is the "I don't know what the hell I'm
    #     supposed to be doing" phase. 
    def create_animations(self):
        
        # Set ourselves into the pose mode of the armature with nothing selected.
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.object.select_pattern(pattern=self.amtname)
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')
        
        euler_rotation_offset = Euler()        
        euler_rotation_offset.x = 0
        euler_rotation_offset.y = 0
        euler_rotation_offset.z = 0
        
        frame_offset = 0
        
        world_transforms = dict()
        bone_transforms  = dict()
        skin_transforms  = dict()
        
        # Go through each Animation.
        for animation in self.animations:
            
            if animation.name != "Idle":
                continue
            
            # Create a new Action for the Animation.
            action = bpy.data.actions.new(name=animation.name)
            
            print("Rendering Animation: " + animation.name + "...")
            
            # Offset counter for each frame.
            #frame_offset = 0
            
            loc_parent_dic = dict() 
            rot_parent_dic = dict()
            mat_parent_dic = dict()
            
            identity = set_identity()
            vec3     = Vector((0.0,1.0,0.0))
            identity = rotate(0.0,vec3,identity)
            
            bone_transforms[0]  = self.bones[self.bone_ids["Root"]].matrix
            world_transforms[0] = self.mul(bone_transforms[0], identity)
            skin_transforms[0]  = self.mul(self.bone_matrix_offset_data[0], world_transforms[0])
            
            frame_offset = 0
            
            # Loop through each frame.
            for frame in animation.frames:
                
                # Bone offset to track which in the frame arrays is being accessed.
                bone_offset = 0 
                
                # Set the current frame in the scene to the offset.
                bpy.data.scenes[0].frame_current = frame_offset
                
                for bone_name in frame.bone_names:
                    
                    if "Root" in bone_name:
                        bone_offset += 1
                        continue
                    
                    # Grab the bone responsible for this action
                    bone = bpy.data.objects[self.amtname].pose.bones[bone_name]

                    bone_id   = self.bone_ids[bone.name]
                    parent_id = self.bone_parent[bone_id]

                    ebone          = self.bones[bone_id]
                    ebone_matrix   = self.bone_matrix_offset_data[bone_id]
                    ebone_location = ebone_matrix.decompose()[0]
                    ebone_rotation = ebone_matrix.decompose()[1]


                    # Create default Parent transform rotation and location                    
                    loc_parent = Vector((0,0,0))
                    rot_parent = Quaternion()
                    mat_parent = self.set_identity()
                    
                    # If the bone indeed has a parent, replace the defaults with parent.
                    #if self.bone_parent[self.bone_ids[bone.name]] != -1:
                        #print(self.bone_names[self.bone_parent[self.bone_ids[bone.name]]])
                        #loc_parent = loc_parent_dic[self.bone_names[self.bone_parent[self.bone_ids[bone.name]]]]
                        #rot_parent = rot_parent_dic[self.bone_names[self.bone_parent[self.bone_ids[bone.name]]]]
                        # mat_parent = mat_parent_dic[self.bone_names[self.bone_parent[self.bone_ids[bone.name]]]]
                    
                    # Grab the raw quaternion and location vector read from the file.
                    loc = frame.bone_locs[bone_offset]
                    rot = frame.bone_rots[bone_offset]
                    mat = frame.bone_mats[bone_offset]
                    
                    self.bone_matrix_bind_pose_data[bone_id]
                    
                    # Bone_transform
                    bt = bone_transforms[bone_id]  = matrix_from_quaternion_position(rot, loc)
                    # World_transform
                    wt = world_transforms[bone_id] = mul(bt,world_transforms[parent_id])
                    # Skin_transform
                    st = skin_transforms[bone_id]  = mul(self.bone_matrix_offset_data[bone_id], wt)
                    
                    print(bone_name + "'s: \t\n" + str(bt))
                    
                    #bone.location            = wt.transposed().decompose()[0]
                    #bone.rotation_quaternion = wt.transposed().decompose()[1]
                    
                    #bone.matrix_basis = st.transposed().copy()
                    
                    #bone.matrix = wt * bt #.transposed()
                    #bone.matrix_basis = wt.transposed()
                    
                    #bt.transpose()
                    #bt.transpose()
                    
                    q = Quaternion()
                    #q = st.decompose()[1]
                    
                    #q.w = st[3][3]
                    #q.z = st[2][3]
                    #q.y = st[1][3]
                    #q.x = st[0][3]
                    
                    q.x = st[3][0]
                    q.y = st[3][1]
                    q.z = st[3][2]
                    q.w = st[3][3]
                    
                    #bt.invert()
                    bone.rotation_quaternion = q
                    
                    #bone.location = Vector((bt[0][3], bt[1][3], bt[2][3]))
                    
                    #bone.matrix = self.translate(ebone_location,src=bone.matrix)
                    #bone.location = Vector((bone.location[0] + ebone_location[0], bone.location[1] + ebone_location[1], bone.location[2] + ebone_location[2]))
                    
                    
                    bone.scale = Vector((1,1,1))
                    #bone.location            = Vector((bt[3][0], bt[3][1], bt[3][2]))
                    
                    #q = bt.inverted().decompose()[1]
                    #q.w = -q.w
                    #q.invert()
                    #q.negate()
                    
                    #bone.rotation_quaternion = q
                    
                    # Set the bones in the dictionaries for future use.
                    loc_parent_dic[bone_name] = loc
                    rot_parent_dic[bone_name] = rot
                    
                    bpy.context.scene.update()
                    
                    bpy.ops.object.select_pattern(pattern=bone_name)
                        
                    # Increment the offset.
                    bone_offset += 1
                
                try:
                    # Create a Blender KeyFrame at this offset.
                    bpy.ops.anim.keyframe_insert_menu(type='BUILTIN_KSI_LocRot')
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
        
        if self.has_armature:
            # Create the Armature for proceeding animation data
            self.create_armature()
        
        #if self.has_animations:
            # WIP for now.
            #self.create_animations()
        
        
        
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
        
        self.hasTex                             = False
        self.has_armature                       = False
        self.has_animations                     = False



class Animation:
    def __init__(self,name,time,frame_count):
        self.name                               = name
        self.time                               = time
        self.frame_count                        = frame_count
        self.key_frames                         = []
        self.frames                             = []
    


class Frame:
    def __init__(self):
        self.bones                              = []
        self.bone_names                         = []
        self.times                              = []    
        self.bone_mats                          = []
        self.bone_locs                          = []
        self.bone_rots                          = []
        
        
        
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
    quat = Quaternion()
    
    quat.x = float(split[0])
    quat.y = float(split[1])
    quat.z = float(split[2])
    quat.w = float(split[3])
    return quat


def read_matrix(file):
    matrix_line = []
    for i in range(0,4):
        matrix_array = []
        string_mat = read_line(file).split(", ")
        matrix_array.append(float(string_mat[0]))
        matrix_array.append(float(string_mat[1]))
        matrix_array.append(float(string_mat[2]))
        matrix_array.append(float(string_mat[3]))
        matrix_line.append((matrix_array[0],matrix_array[1],matrix_array[2],matrix_array[3]))
    return Matrix((matrix_line[0], matrix_line[1], matrix_line[2], matrix_line[3]))

#####################################################################################
###                                                                               ###
###   Matrix methods                                                              ###
###       (Note: Java-translated methods to test accuracy of Animation code.)     ###
###        Will likely get rid of these.                                          ###
###                                                                               ###
#####################################################################################
    
def matrix_from_quaternion_position(quaternion, position):
    
    mat = matrix_from_quaternion(quaternion)
    mat2 = set_identity()
    mat2 = translate(position, mat2)
    #mat2 = mat2.transposed().copy()
    #print(mat)
    #mat3 = mat2 * mat
    mat3 = mul(mat2, mat)
    return mat3


def translate(vec,src=None):
    
    m = Matrix.Identity(4)
    set_identity(m)
    
    if src == None:
        set_identity(src)
    
    m[3][0] += src[0][0] * vec.x + src[1][0] * vec.y + src[2][0] * vec.z
    m[3][1] += src[0][1] * vec.x + src[1][1] * vec.y + src[2][1] * vec.z
    m[3][2] += src[0][2] * vec.x + src[1][2] * vec.y + src[2][2] * vec.z
    m[3][3] += src[0][3] * vec.x + src[1][3] * vec.y + src[2][3] * vec.z

    return m

def length(quat):
    return math.sqrt(quat.x * quat.x + quat.y * quat.y + quat.z * quat.z + quat.w * quat.w)


def matrix_from_quaternion(quaternion):
    
    m = set_identity()
    
    q = quaternion
    
    if length(quaternion) > 0.0:
        q = quaternion.normalized()
    
    xx = (q.x) * (q.x)
    xy = (q.x) * (q.y)
    xz = (q.x) * (q.z)
    wx = (q.x) * (q.w)
    
    yy = (q.y) * (q.y)
    yz = (q.y) * (q.z)
    wy = (q.y) * (q.w)
    
    zz = (q.z) * (q.z)
    wz = (q.z) * (q.w)
    
    m[0][0] = 1.0 - 2.0 * (float(yy) + float(zz))
    m[1][0] =       2.0 * (float(xy) - float(wz))
    m[2][0] =       2.0 * (float(xz) + float(wy))
    m[3][0] = 0.0
    
    m[0][1] =       2.0 * (float(xy) + float(wz))
    m[1][1] = 1.0 - 2.0 * (float(xx) + float(zz))
    m[2][1] =       2.0 * (float(yz) - float(wx)) * float(1.0)
    m[3][1] = 0.0
    
    m[0][2] =       2.0 * (float(xz) - float(wy))
    m[1][2] =       2.0 * (float(yz) + float(wx))
    m[2][2] = 1.0 - 2.0 * (float(xx) + float(yy))
    m[3][2] = 0.0
    
    m[0][3] = 0.0
    m[1][3] = 0.0
    m[2][3] = 0.0
    m[3][3] = 1.0
    
    return m.transposed().copy()


def rotate(angle, axis, src):
    m = set_identity()
    
    c = math.cos(angle)
    s = math.sin(angle)
    oneminusc = 1.0 - c
    
    xy = axis[0] * axis[1]
    yz = axis[1] * axis[2]
    xz = axis[0] * axis[2]
    
    xs = axis[0] * s
    ys = axis[1] * s
    zs = axis[2] * s
    
    f00 = axis[0] * axis[0] * oneminusc + c
    f01 = xy * oneminusc + zs
    f02 = xz * oneminusc - ys
    
    f10 = xy * oneminusc - zs
    f11 = axis[1] * axis[1] * oneminusc + c
    f12 = yz * oneminusc + xs
    
    f20 = xz * oneminusc + ys
    f21 = yz * oneminusc - xs
    f22 = axis[2] * axis[2] * oneminusc + c
    
    t00 = src[0][0] * f00 + src[1][0] * f01 + src[2][0] * f02
    t01 = src[0][1] * f00 + src[1][1] * f01 + src[2][1] * f02
    t02 = src[0][2] * f00 + src[1][2] * f01 + src[2][2] * f02
    t03 = src[0][3] * f00 + src[1][3] * f01 + src[2][3] * f02
    
    t10 = src[0][0] * f10 + src[1][0] * f11 + src[2][0] * f12
    t11 = src[0][1] * f10 + src[1][1] * f11 + src[2][1] * f12
    t12 = src[0][2] * f10 + src[1][2] * f11 + src[2][2] * f12
    t13 = src[0][3] * f10 + src[1][3] * f11 + src[2][3] * f12
    
    m[2][0] = (src[0][0] * f20 + src[1][0] * f21 + src[2][0] * f22)
    m[2][1] = (src[0][1] * f20 + src[1][1] * f21 + src[2][1] * f22)
    m[2][2] = (src[0][2] * f20 + src[1][2] * f21 + src[2][2] * f22)
    m[2][3] = (src[0][3] * f20 + src[1][3] * f21 + src[2][3] * f22)
    
    m[0][0] = t00
    m[0][1] = t01
    m[0][2] = t02
    m[0][3] = t03
    
    m[1][0] = t10
    m[1][1] = t11
    m[1][2] = t12
    m[1][3] = t13
    
    return m


def mul(left,right,dest=Matrix.Identity(4)):
    if dest == None:
        dest = set_identity()
    
    dest[0][0] = left[0][0] * right[0][0] + left[1][0] * right[0][1] + left[2][0] * right[0][2] + left[3][0] * right[0][3]
    dest[0][1] = left[0][1] * right[0][0] + left[1][1] * right[0][1] + left[2][1] * right[0][2] + left[3][1] * right[0][3]
    dest[0][2] = left[0][2] * right[0][0] + left[1][2] * right[0][1] + left[2][2] * right[0][2] + left[3][2] * right[0][3]
    dest[0][3] = left[0][3] * right[0][0] + left[1][3] * right[0][1] + left[2][3] * right[0][2] + left[3][3] * right[0][3]
    dest[1][0] = left[0][0] * right[1][0] + left[1][0] * right[1][1] + left[2][0] * right[1][2] + left[3][0] * right[1][3]
    dest[1][1] = left[0][1] * right[1][0] + left[1][1] * right[1][1] + left[2][1] * right[1][2] + left[3][1] * right[1][3]
    dest[1][2] = left[0][2] * right[1][0] + left[1][2] * right[1][1] + left[2][2] * right[1][2] + left[3][2] * right[1][3]
    dest[1][3] = left[0][3] * right[1][0] + left[1][3] * right[1][1] + left[2][3] * right[1][2] + left[3][3] * right[1][3]
    dest[2][0] = left[0][0] * right[2][0] + left[1][0] * right[2][1] + left[2][0] * right[2][2] + left[3][0] * right[2][3]
    dest[2][1] = left[0][1] * right[2][0] + left[1][1] * right[2][1] + left[2][1] * right[2][2] + left[3][1] * right[2][3]
    dest[2][2] = left[0][2] * right[2][0] + left[1][2] * right[2][1] + left[2][2] * right[2][2] + left[3][2] * right[2][3]
    dest[2][3] = left[0][3] * right[2][0] + left[1][3] * right[2][1] + left[2][3] * right[2][2] + left[3][3] * right[2][3]
    dest[3][0] = left[0][0] * right[3][0] + left[1][0] * right[3][1] + left[2][0] * right[3][2] + left[3][0] * right[3][3]
    dest[3][1] = left[0][1] * right[3][0] + left[1][1] * right[3][1] + left[2][1] * right[3][2] + left[3][1] * right[3][3]
    dest[3][2] = left[0][2] * right[3][0] + left[1][2] * right[3][1] + left[2][2] * right[3][2] + left[3][2] * right[3][3]
    dest[3][3] = left[0][3] * right[3][0] + left[1][3] * right[3][1] + left[2][3] * right[3][2] + left[3][3] * right[3][3]
    
    return dest


def set_identity(mat=Matrix.Identity(4)):
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
    return mat