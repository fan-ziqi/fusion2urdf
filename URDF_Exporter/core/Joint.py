# -*- coding: utf-8 -*-
"""
Created on Sun May 12 20:17:17 2019

@author: syuntoku
"""

import adsk, re
from xml.etree.ElementTree import Element, SubElement
from ..utils import utils

class Joint:
    def __init__(self, name, xyz, axis, parent, child, joint_type, upper_limit, lower_limit):
        """
        Attributes
        ----------
        name: str
            name of the joint
        type: str
            type of the joint(ex: rev)
        xyz: [x, y, z]
            coordinate of the joint
        axis: [x, y, z]
            coordinate of axis of the joint
        parent: str
            parent link
        child: str
            child link
        joint_xml: str
            generated xml describing about the joint
        tran_xml: str
            generated xml describing about the transmission
        """
        self.name = name
        self.type = joint_type
        self.xyz = xyz
        self.parent = parent
        self.child = child
        self.joint_xml = None
        self.tran_xml = None
        self.axis = axis  # for 'revolute' and 'continuous'
        self.upper_limit = upper_limit  # for 'revolute' and 'prismatic'
        self.lower_limit = lower_limit  # for 'revolute' and 'prismatic'

    def make_joint_xml(self):
        """
        Generate the joint_xml and hold it by self.joint_xml
        """
        joint = Element('joint')
        joint.attrib = {'name':self.name, 'type':self.type}

        origin = SubElement(joint, 'origin')
        origin.attrib = {'xyz':' '.join([str(_) for _ in self.xyz]), 'rpy':'0 0 0'}
        parent = SubElement(joint, 'parent')
        parent.attrib = {'link':self.parent}
        child = SubElement(joint, 'child')
        child.attrib = {'link':self.child}
        if self.type == 'revolute' or self.type == 'continuous' or self.type == 'prismatic':
            axis = SubElement(joint, 'axis')
            axis.attrib = {'xyz':' '.join([str(_) for _ in self.axis])}
        if self.type == 'revolute' or self.type == 'prismatic':
            limit = SubElement(joint, 'limit')
            limit.attrib = {'upper': str(self.upper_limit), 'lower': str(self.lower_limit),
                            'effort': '100', 'velocity': '100'}

        self.joint_xml = "\n".join(utils.prettify(joint).split("\n")[1:])

    def make_transmission_xml(self):
        """
        Generate the tran_xml and hold it by self.tran_xml


        Notes
        -----------
        mechanicalTransmission: 1
        type: transmission interface/SimpleTransmission
        hardwareInterface: PositionJointInterface
        """

        tran = Element('transmission')
        tran.attrib = {'name':self.name + '_tran'}

        joint_type = SubElement(tran, 'type')
        joint_type.text = 'transmission_interface/SimpleTransmission'

        joint = SubElement(tran, 'joint')
        joint.attrib = {'name':self.name}
        hardwareInterface_joint = SubElement(joint, 'hardwareInterface')
        hardwareInterface_joint.text = 'hardware_interface/EffortJointInterface'

        actuator = SubElement(tran, 'actuator')
        actuator.attrib = {'name':self.name + '_actr'}
        hardwareInterface_actr = SubElement(actuator, 'hardwareInterface')
        hardwareInterface_actr.text = 'hardware_interface/EffortJointInterface'
        mechanicalReduction = SubElement(actuator, 'mechanicalReduction')
        mechanicalReduction.text = '1'

        self.tran_xml = "\n".join(utils.prettify(tran).split("\n")[1:])


def make_joints_dict(root, msg):
    """
    joints_dict holds parent, axis and xyz informatino of the joints


    Parameters
    ----------
    root: adsk.fusion.Design.cast(product)
        Root component
    msg: str
        Tell the status

    Returns
    ----------
    joints_dict:
        {name: {type, axis, upper_limit, lower_limit, parent, child, xyz}}
    msg: str
        Tell the status
    """

    joint_type_list = [
    'fixed', 'revolute', 'prismatic', 'Cylinderical',
    'PinSlot', 'Planner', 'Ball']  # these are the names in urdf

    joints_dict = {}

    for joint in root.joints:
        joint_dict = {}
        joint_type = joint_type_list[joint.jointMotion.jointType]
        joint_dict['type'] = joint_type

        # swhich by the type of the joint
        joint_dict['axis'] = [0, 0, 0]
        joint_dict['upper_limit'] = 0.0
        joint_dict['lower_limit'] = 0.0

        # support  "Revolute", "Rigid" and "Slider"
        if joint_type == 'revolute':
            joint_dict['axis'] = [round(i, 6) for i in \
                joint.jointMotion.rotationAxisVector.asArray()] ## In Fusion, exported axis is normalized.
            max_enabled = joint.jointMotion.rotationLimits.isMaximumValueEnabled
            min_enabled = joint.jointMotion.rotationLimits.isMinimumValueEnabled
            if max_enabled and min_enabled:
                joint_dict['upper_limit'] = round(joint.jointMotion.rotationLimits.maximumValue, 6)
                joint_dict['lower_limit'] = round(joint.jointMotion.rotationLimits.minimumValue, 6)
            elif max_enabled and not min_enabled:
                msg = joint.name + 'is not set its lower limit. Please set it and try again.'
                break
            elif not max_enabled and min_enabled:
                msg = joint.name + 'is not set its upper limit. Please set it and try again.'
                break
            else:  # if there is no angle limit
                joint_dict['type'] = 'continuous'

        elif joint_type == 'prismatic':
            joint_dict['axis'] = [round(i, 6) for i in \
                joint.jointMotion.slideDirectionVector.asArray()]  # Also normalized
            max_enabled = joint.jointMotion.slideLimits.isMaximumValueEnabled
            min_enabled = joint.jointMotion.slideLimits.isMinimumValueEnabled
            if max_enabled and min_enabled:
                joint_dict['upper_limit'] = round(joint.jointMotion.slideLimits.maximumValue/100, 6)
                joint_dict['lower_limit'] = round(joint.jointMotion.slideLimits.minimumValue/100, 6)
            elif max_enabled and not min_enabled:
                msg = joint.name + 'is not set its lower limit. Please set it and try again.'
                break
            elif not max_enabled and min_enabled:
                msg = joint.name + 'is not set its upper limit. Please set it and try again.'
                break
        elif joint_type == 'fixed':
            pass

        if joint.occurrenceTwo.component.name == 'base_link':
            joint_dict['parent'] = 'base_link'
        else:
            # joint_dict['parent'] = re.sub('[ :()]', '_', joint.occurrenceTwo.name)
            joint_dict['parent'] = re.sub(r'\s*\(\d+\)|:\d+$', '', joint.occurrenceTwo.name)
        # joint_dict['child'] = re.sub('[ :()]', '_', joint.occurrenceOne.name)
        joint_dict['child'] = re.sub(r'\s*\(\d+\)|:\d+$', '', joint.occurrenceOne.name)


        #There seem to be a problem with geometryOrOriginTwo. To calcualte the correct orogin of the generated stl files following approach was used.
        #https://forums.autodesk.com/t5/fusion-360-api-and-scripts/difference-of-geometryororiginone-and-geometryororiginonetwo/m-p/9837767
        #Thanks to Masaki Yamamoto!

        # Coordinate transformation by matrix
        # M: 4x4 transformation matrix
        # a: 3D vector
        def trans(M, a):
            ex = [M[0],M[4],M[8]]
            ey = [M[1],M[5],M[9]]
            ez = [M[2],M[6],M[10]]
            oo = [M[3],M[7],M[11]]
            b = [0, 0, 0]
            for i in range(3):
                b[i] = a[0]*ex[i]+a[1]*ey[i]+a[2]*ez[i]+oo[i]
            return(b)


        # Returns True if two arrays are element-wise equal within a tolerance
        def allclose(v1, v2, tol=1e-6):
            return( max([abs(a-b) for a,b in zip(v1, v2)]) < tol )

        try:
            xyz_from_one_to_joint = joint.geometryOrOriginOne.origin.asArray() # Relative Joint pos
            xyz_from_two_to_joint = joint.geometryOrOriginTwo.origin.asArray() # Relative Joint pos
            xyz_of_one            = joint.occurrenceOne.transform.translation.asArray() # Link origin
            xyz_of_two            = joint.occurrenceTwo.transform.translation.asArray() # Link origin
            M_two = joint.occurrenceTwo.transform.asArray() # Matrix as a 16 element array.

        # Compose joint position
            case1 = allclose(xyz_from_two_to_joint, xyz_from_one_to_joint)
            case2 = allclose(xyz_from_two_to_joint, xyz_of_one)
            if case1 or case2:
                xyz_of_joint = xyz_from_two_to_joint
            else:
                xyz_of_joint = trans(M_two, xyz_from_two_to_joint)


            joint_dict['xyz'] = [round(i / 100.0, 6) for i in xyz_of_joint]  # converted to meter

        except:
            try:
                if type(joint.geometryOrOriginTwo)==adsk.fusion.JointOrigin:
                    data = joint.geometryOrOriginTwo.geometry.origin.asArray()
                else:
                    data = joint.geometryOrOriginTwo.origin.asArray()
                joint_dict['xyz'] = [round(i / 100.0, 6) for i in data]  # converted to meter
            except:
                msg = joint.name + " doesn't have joint origin. Please set it and run again."
                break

        joints_dict[joint.name] = joint_dict
    return joints_dict, msg
