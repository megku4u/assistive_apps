#!/usr/bin/env python

# import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import mpl_toolkits.mplot3d.axes3d as p3
import matplotlib.animation as animation
import matplotlib.patches as mpatches
from os import path
from tf.transformations import quaternion_from_euler, quaternion_matrix, translation_from_matrix, quaternion_from_matrix
from rospkg import RosPack
#from mobility_games.utils.helper_functions import convert_pose_inverse_transform, convert_translation_rotation_to_pose, invert_transform_2


class G2O_Error_Viz:
    def __init__(self, g2o_result_path, g2o_data_path, test_path, manual_rotation):
        top = RosPack().get_path("navigation_prototypes")
        self.vertices = {}
        self.old_vertices = {}
        self.old_edges = {}
        self.new_edges = {}
        self.old_AR = {}
        self.new_AR = {}
        self.transdifference = []
        self.rotdifference = []
        self.AR_Edges = {}
        self.dummyidlist = []
        self.g2o_result_path = path.join(top, g2o_result_path)
        self.g2o_data_path = path.join(top, g2o_data_path)
        self.testlist = []
        self.test_traj = []
        self.test_path = path.join(top, test_path)
        self.origin_info = None
        self.vertex_id_start = 587
        self.manual_rotation = manual_rotation

    def GatherData(self):
        self.vertices = {}
        self.old_edges = {}
        self.old_vertices = {}
        self.testlist = []
        origin_tag = None
        with open(self.g2o_result_path, 'rb') as g2o_result:
            for line in g2o_result:
                if line.startswith("FIX "):
                    line = line.strip()
                    line = line.split(' ')
                    dummyid = int(line[1])
                    if dummyid >= self.vertex_id_start:
                        self.dummyidlist.append(dummyid)
                    else:
                        origin_tag = dummyid
        with open(self.g2o_result_path, 'rb') as g2o_result:
            for line in g2o_result:
                if line.startswith("VERTEX_SE3:QUAT "):
                    line = line.strip()
                    line = line.split()
                    newline = []
                    for data in line[1:]:
                        newline.append(float(data))
                    if not newline[0] in self.dummyidlist:
                        if newline[0] == origin_tag:
                            self.origin_info = (tuple(newline[1:4]), tuple(newline[4:8]))
                        if newline[0] >= self.vertex_id_start:
                            self.vertices[int(newline[0])] = (tuple(newline[1:4]), tuple(newline[4:8]))
                            # print("found vertex: " + str(newline[0]))
                        else:
                            self.new_AR[int(newline[0])] = (tuple(newline[1:4]), tuple(newline[4:8]))
                            print("found tag: " + str(newline[0]))
                elif line.startswith("EDGE_SE3:QUAT "):
                    line = line.strip()
                    line = line.split()
                    newline = []
                    for data in line[1:]:
                        newline.append(float(data))
                    if not newline[1] in self.dummyidlist:
                        if int(newline[0]) + 2 == int(newline[1]):
                            self.old_edges[int(newline[0])] = (tuple(newline[2:5]), tuple(newline[5:9]))
                            print("found edge: " + str(newline[0]))
                        else:
                            self.AR_Edges[int(newline[0])] = (newline[1], tuple(newline[2:5]), tuple(newline[5:9]))
        with open(self.g2o_data_path, 'rb') as g2o_data:
            for line in g2o_data:
                if line.startswith("VERTEX_SE3:QUAT "):
                    line = line.strip()
                    line = line.split()
                    newline = []
                    for data in line[1:]:
                        newline.append(float(data))
                    if newline[0] >= self.vertex_id_start:
                        self.old_vertices[int(newline[0])] = (tuple(newline[1:4]), tuple(newline[4:8]))
                        # print("found vertex: " + str(line[0]))
                    # else:
                    #    self.old_AR[int(line[0])] = (tuple(line[1:4]), tuple(line[4:8]))
                    #    print("found tag: " + str(line[0]))
        with open(self.test_path, 'rb') as test_data:
            for line in test_data:
                if line.startswith("TAG "):
                    line = line.strip()
                    newline = []
                    for data in line.split()[1:]:
                        newline.append(float(data))
                    transrot = (newline[0:3], newline[3:])
                    rotation = ((0, 0, 0), quaternion_from_euler(*self.manual_rotation))
                    origin_rotated = self.MultiplyTransform(self.origin_info, rotation)
                    matres = self.MultiplyTransform(origin_rotated, transrot)
                    self.testlist.append(np.hstack((matres[0], matres[1])))
                elif line.startswith("PATH "):
                    line = line.strip()
                    newline = []
                    for data in line.split()[1:]:
                        newline.append(float(data))
                    transrot = (newline[0:3], newline[3:])
                    rotation = ((0, 0, 0), quaternion_from_euler(*self.manual_rotation))
                    origin_rotated = self.MultiplyTransform(self.origin_info, rotation)
                    matres = self.MultiplyTransform(origin_rotated, transrot)
                    self.test_traj.append(np.hstack((matres[0], matres[1])))

    """def CalculateNewEdges(self):
        self.new_edges = {}
        ind = self.vertex_id_start
        i = 0
        #print(self.vertices.keys())
        while i < len(self.old_edges.keys()):
            pose = convert_translation_rotation_to_pose(self.vertices[ind][0], self.vertices[ind][1])
            #print(self.vertices[ind][1])
            #print pose
            (trans, rot) = convert_pose_inverse_transform(pose)
            (trans2, rot2) = self.vertices[ind+1]
            #print(rot)

            T0_1 = quaternion_matrix(rot)
            T0_1[:-1, -1] = np.asarray(trans).T

            T2_0 = quaternion_matrix(rot2)
            T2_0[:-1, -1] = np.asarray(trans2)
            #print T2_0
            #print T0_1

            FinTransform = np.matmul(T0_1, T2_0)
            #print FinTransform

            rot_fin = tuple(quaternion_from_matrix(FinTransform))
            trans_fin = tuple(translation_from_matrix(FinTransform))
            self.new_edges[ind] = (trans_fin, rot_fin)
            #print("comparison: %s" % ind)
            #print(rot_fin)
            #print(self.old_edges[ind][1])

            ind += 1
            i += 1
    def Calculate_Old_Vertices(self):
        # TODO make function for finding the old vertex locations based on the old edges.
        ind = self.vertex_id_start
        i = 0
        #print(self.vertices.keys())
        fixpoint = self.vertices[0]
        while i < len(self.old_edges.keys()):
            pose = convert_translation_rotation_to_pose(self.old_edges[ind], self.vertices[ind])
            #print(self.vertices[ind][1])
            #print pose
            (trans, rot) = convert_pose_inverse_transform(pose)
            (trans2, rot2) = self.vertices[ind+1]
            #print(rot)

            T0_1 = quaternion_matrix(rot)
            T0_1[:-1, -1] = np.asarray(trans).T

            T2_0 = quaternion_matrix(rot2)
            T2_0[:-1, -1] = np.asarray(trans2)
            #print T2_0
            #print T0_1

            FinTransform = np.matmul(T0_1, T2_0)
            #print FinTransform

            rot_fin = tuple(quaternion_from_matrix(FinTransform))
            trans_fin = tuple(translation_from_matrix(FinTransform))
            self.new_edges[ind] = (trans_fin, rot_fin)
            #print("comparison: %s" % ind)
            #print(rot_fin)
            #print(self.old_edges[ind][1])

            ind += 1
            i += 1
        pass"""

    """def CalculateDifference(self):
        ind = self.vertex_id_start
        i = 0
        #len(self.old_edges.keys())
        self.transdifference = []
        self.rotdifference = []
        while i < len(self.old_edges.keys()):
            transdiff = [self.new_edges[ind][0][j] - self.old_edges[ind][0][j] for j in range(3)]
            #print(transdiff)
            euler_rot0 = euler_from_quaternion(self.old_edges[ind][1])
            euler_rot1 = euler_from_quaternion(self.new_edges[ind][1])
            rotdiff = euler_rot1[2] - euler_rot0[2]

            self.transdifference.append(np.linalg.norm(np.asarray(transdiff)))
            self.rotdifference.append(rotdiff)
            ind += 1
            i += 1"""

    def MultiplyTransform(self, tr1, tr2):
        T = quaternion_matrix(tr1[1])
        T[:-1, -1] = np.squeeze(np.asarray(tr1[0]))

        T2 = quaternion_matrix(tr2[1])
        T2[:-1, -1] = np.squeeze(np.asarray(tr2[0]))

        Tres = np.matmul(T, T2)
        trans = translation_from_matrix(Tres)
        rot = quaternion_from_matrix(Tres)

        return (trans, rot)

    def run(self):
        self.GatherData()
        # self.CalculateNewEdges()
        ordered_vertices = []
        old_ordered_vertices = []

        for key in sorted(self.vertices):
            ordered_vertices.append(self.vertices[key][0])
            old_ordered_vertices.append(self.old_vertices[key][0])
        traj_data = np.asarray(ordered_vertices)
        old_traj_data = np.asarray(old_ordered_vertices)
        test_traj_data = np.asarray(self.test_traj)  # np.asarray(self.testlist)
        for i in self.AR_Edges.items():
            tag_id = int(i[1][0])
            pose_id = int(i[0])
            detections = self.old_AR.get(tag_id, -1)
            if detections == -1:
                detections = [self.MultiplyTransform(self.old_vertices[pose_id], i[1][1:])]
            else:
                res = self.MultiplyTransform(self.old_vertices[pose_id], i[1][1:])
                detections.append(res)
            self.old_AR[tag_id] = detections
        test_AR = np.asarray(self.testlist)
        # print self.old_AR
        # self.CalculateDifference()
        # print("final info: ")
        # print("translations: %s" % str(self.transdifference))
        # print("rotations: %s" % str(self.rotdifference))
        # Two subplots, the axes array is 1-d
        # f, axarr = plt.subplots(, sharex=True)
        # axarr[0].plot(x, y)
        # axarr[0].set_title('Sharing X axis')
        # axarr[1].scatter(x, y)
        fig = plt.figure()
        ax = p3.Axes3D(fig)
        """for tag in self.old_AR.items():
            for detection in tag[1]:
                point = detection[0]
                print(("tag_%i: %s") % (tag[0], point))
                plt.plot((point[0],), (point[1],), (point[2],), 'ro')
                ax.text(point[0], point[1], point[2], tag[0])"""
        for tag in self.new_AR.items():
            point = tag[1][0]
            plt.plot((point[0],), (point[1],), (point[2],), 'bo')
            ax.text(point[0], point[1], point[2], tag[0])
        #test_tags, = plt.plot(test_AR[:, 0], test_AR[:, 1], test_AR[:, 2], 'mo', label='naive Test Tags')
        print(np.shape(traj_data))
        new_path, = plt.plot(traj_data[:, 0], traj_data[:, 1], traj_data[:, 2], 'b-', label='corrected trajectory')
        # old_path, = plt.plot(old_traj_data[:,0], old_traj_data[:,1], old_traj_data[:,2], 'r--', label = 'original trajectory')
        print (np.shape(test_traj_data))
        test_path, = plt.plot(test_traj_data[:, 0], test_traj_data[:, 1], test_traj_data[:, 2], 'm--',label='naive approach trajectory')
        plt.legend(handles=[new_path, test_path])  # old_path,
        #plt.legend(handles=[new_path])
        plt.xlabel('X')
        plt.ylabel('Y')
        # plt.zlabel('Z')
        plt.title('G2O Trajectory Plot')
        plt.grid(True)

        plt.show()


if __name__ == "__main__":
    g2o_viz = G2O_Error_Viz()
    g2o_viz.run()
