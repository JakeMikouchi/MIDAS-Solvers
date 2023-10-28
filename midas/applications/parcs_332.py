import os
import gc
import sys
import copy
import h5py
import math
import time
import numpy as np
import pickle
import random
from pathlib import Path
import shutil 
from matplotlib import pyplot as plt
import subprocess
from subprocess import PIPE, STDOUT
from midas.utils.solution_types import Solution
from midas.utils.lcoe import LCOE, LCOE_MCYC

class Loading_Pattern_Solution(Solution):
    """
    Solution class for designing loading patterns using PARCS code.

    Parameters: None

    Written by Gregory Delipei. 01/08/2022
    """
    def __init__(self):
        Solution.__init__(self)
        self.type        = None
        self.number_pins = None
        self.model       = None
        self.symmetry    = None
        self.nrow=17
        self.ncol=17
        self.action_lower=-1
        self.action_upper=1
        self.core_dict={}
       
    def add_additional_information(self,settings):
        """
        Adds information on reactor parameters.

        Parameters
            settings: The settings dictionary for the parameters.
        
        Written by Gregory Delipei. 01/08/2022
        """
        self.symmetry=settings["genome"]["parcs_data"]["symmetry"]
        self.core_dict['core_map'], self.core_dict['core_id'] = self.generate_core()
        if 'inventory' in list(settings["genome"].keys()):
            self.core_dict['Inventory'] = settings["genome"]['inventory']
        else:
            inventory = {}
            for key,value in settings["genome"]["chromosomes"].items():
                inv_it = {}
                inv_it['Max_Limit']=np.inf
                inv_it['In_Design']=0
                inv_it['Cost']=250
                inv_it['Tag']=str(value['type'])
                inv_it['Cross_Section']=value['serial']
                inventory[key]=inv_it
            self.core_dict['Inventory'] = inventory
       
        info = settings['genome']['parcs_data']
        if 'xs_library' in info:
            self.library = info['xs_library']
        if 'power' in info:
            self.power = float(info['power'])
        if 'flow' in info:
            self.flow = float(info['flow'])
        if 'inlet_temperature' in info:
            self.inlet_temperature = float(info['inlet_temperature'])
        if 'map_size' in info:
            self.map_size= info['map_size']
        if 'number_assemblies' in info:
            self.number_assemblies = int(info['number_assemblies'])

        if 'fixed_problem' == settings['optimization']['reproducer']:
            self.fixed_genome = True
        elif 'unique_genes' == settings['optimization']['reproducer']:
            self.fixed_genome = True

    def generate_core(self):
        """
        Generates the 17x17 core map with consistent identifiers and treatment of symmetry.

        Parameters: None
        Additional comments:
          - The core_map is manually defined as a list line by line starting from the top of the core.
          It is advised to use the following naming conention for reflector assemblies 'ABCDE' 
          with A being R, BC indicating the row number (00-17) and DE the column number (00-17). For 
          the fuel assemblies it is advised to use the following naming convention 'ABC' with A being the 
          row letter indetifier (A-O) and BC being the column number (00-17). 

        Written by Gregory Delipei 7/12/2022
        """
        core_map = [  None ,  None ,  None ,  None ,"R0004","R0005","R0006","R0007","R0008","R0009","R0010","R0011","R0012",  None ,  None ,  None ,  None ,
                      None ,  None ,"R0102","R0103","R0104", "A05" , "A06" , "A07" , "A08" , "A09" , "A10" , "A11" ,"R0112","R0113","R0114",  None ,  None ,
                      None ,"R0201","R0202", "B03" , "B04" , "B05" , "B06" , "B07" , "B08" , "B09" , "B10" , "B11" , "B12" , "B13" ,"R0214","R0215",  None ,
                      None ,"R0301", "C02" , "C03" , "C04" , "C05" , "C06" , "C07" , "C08" , "C09" , "C10" , "C11" , "C12" , "C13" , "C14" ,"R0315",  None ,
                    "R0400","R0401", "D02" , "D03" , "D04" , "D05" , "D06" , "D07" , "D08" , "D09" , "D10" , "D11" , "D12" , "D13" , "D14" ,"R0415","R0416",
                    "R0500", "E01" , "E02" , "E03" , "E04" , "E05" , "E06" , "E07" , "E08" , "E09" , "E10" , "E11" , "E12" , "E13" , "E14" , "E15" ,"R0516",
                    "R0600", "F01" , "F02" , "F03" , "F04" , "F05" , "F06" , "F07" , "F08" , "F09" , "F10" , "F11" , "F12" , "F13" , "F14" , "F15" ,"R0616",
                    "R0700", "G01" , "G02" , "G03" , "G04" , "G05" , "G06" , "G07" , "G08" , "G09" , "G10" , "G11" , "G12" , "G13" , "G14" , "G15" ,"R0716",
                    "R0800", "H01" , "H02" , "H03" , "H04" , "H05" , "H06" , "H07" , "H08" , "H09" , "H10" , "H11" , "H12" , "H13" , "H14" , "H15" ,"R0816",
                    "R0900", "I01" , "I02" , "I03" , "I04" , "I05" , "I06" , "I07" , "I08" , "I09" , "I10" , "I11" , "I12" , "I13" , "I14" , "I15" ,"R0916",
                    "R1000", "J01" , "J02" , "J03" , "J04" , "J05" , "J06" , "J07" , "J08" , "J09" , "J10" , "J11" , "J12" , "J13" , "J14" , "J15" ,"R1016",
                    "R1100", "K01" , "K02" , "K03" , "K04" , "K05" , "K06" , "K07" , "K08" , "K09" , "K10" , "K11" , "K12" , "K13" , "K14" , "K15" ,"R1116",
                    "R1200","R1201", "L02" , "L03" , "L04" , "L05" , "L06" , "L07" , "L08" , "L09" , "L10" , "L11" , "L12" , "L13" , "L14" ,"R1215","R1216",
                      None ,"R1301", "M02" , "M03" , "M04" , "M05" , "M06" , "M07" , "M08" , "M09" , "M10" , "M11" , "M12" , "M13" , "M14" ,"R1315",  None ,
                      None ,"R1401","R1402", "N03" , "N04" , "N05" , "N06" , "N07" , "N08" , "N09" , "N10" , "N11" , "N12" , "N13" ,"R1414","R1415",  None ,
                      None ,  None ,"R1502","R1503","R1504", "O05" , "O06" , "O07" , "O08" , "O09" , "O10" , "O11" ,"R1512","R1513","R1514",  None ,  None ,
                      None ,  None ,  None ,  None ,"R1604","R1605","R1606","R1607","R1608","R1609","R1610","R1611","R1612",  None ,  None ,  None ,  None ]
        core_map = np.array(core_map).reshape((self.nrow,self.ncol))
        core_id = []
        for i in range(self.nrow-1,-1,-1):
            for j in range(self.ncol):
                core_id.append((i-8,j-8))
        core_id=np.array(core_id).reshape((self.nrow,self.ncol,2))
        if self.symmetry == 'quarter':
            self.core_dict['core'], self.core_dict['fuel'] = self.quarter_core(core_map,core_id)
        elif self.symmetry == 'octant':
            self.symmetry_axes = ((8,8),(16,16),(16,8))
            self.core_dict['core'], self.core_dict['fuel'] = self.octant_core(core_map,core_id)
        else:
            raise ValueError(
                f"The selected symmetry ({self.symmetry}) is not valid."
            )
        return(core_map, core_id)

    def get_full_core(self):
        """
        Generates the 17x17 full fuel core from symmetry.

        Parameters: None
    
        Written by Gregory Delipei 7/24/2022
        """
        full_core  = {}
        for key, value in self.core_dict['fuel'].items():
            full_core[key]=value['Value']
            for skey in value['Symmetric_Assemblies']:
               full_core[skey]=value['Value'] 
        return(full_core)

    def quarter_core(self,core_map,core_id):
        """
        Generates the quarter core symmetry map.

        Parameters: 
           - core_map: a 17x17 numpy array with the fuel assembly location names.
           - core_id: a 17x17x2 numpy array with coordinate indices for each fuel assembly location
           ranging from -8 to +8.

        Written by Gregory Delipei 7/12/2022
        """
        sym_center = self.symmetry_axes[0]
        sym_horizontal = self.symmetry_axes[1]
        sym_vertical = self.symmetry_axes[2]
        if sym_vertical[0] > sym_center[0]:
            row_iter = np.arange(sym_center[0],sym_vertical[0]+1,1)
        else:
            row_iter = np.arange(sym_center[0],sym_vertical[0]-1,-1)
        if sym_horizontal[1] > sym_center[1]:
            col_iter = np.arange(sym_center[1],sym_horizontal[1]+1,1)
        else:
            col_iter = np.arange(sym_center[1],sym_horizontal[1]-1,-1)

        core_dict={}
        for irow in row_iter:
            for icol in col_iter:
                dict_value={'Symmetric_Assemblies':[],
                            'Value': None}
                if (irow,icol) == sym_center:
                    pass
                elif irow == sym_horizontal[0] and icol != sym_center[1]:                 
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == idy) & (core_id[:,:,1] == -idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0]]
                elif icol == sym_vertical[1] and irow != sym_center[0]:
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0]]
                else:
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    idxy_2= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == -idx))
                    idxy_3= np.where((core_id[:,:,0] == idy) & (core_id[:,:,1] == -idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0], core_map[idxy_2][0], core_map[idxy_3][0]]
                core_dict[core_map[irow,icol]] = dict_value
                fuel_dict = self.extract_fuel(core_dict)
        return(core_dict,fuel_dict)
        
    def octant_core(self, core_map, core_id):
        """
        Generates the octant core symmetry map.

        Parameters: 
           - core_map: a 17x17 numpy array with the fuel assembly location names.
           - core_id: a 17x17x2 numpy array with coordinate indices for each fuel assembly location
           ranging from -8 to +8.

        Written by Gregory Delipei 7/12/2022
        """
        sym_center = self.symmetry_axes[0]
        sym_corner = self.symmetry_axes[1]
        sym_vertical = self.symmetry_axes[2]
        if sym_corner[0] > sym_center[0]:
            row_iter = np.arange(sym_center[0],sym_corner[0]+1,1)
        else:
            row_iter = np.arange(sym_center[0],sym_corner[0]-1,-1)
        if sym_corner[1] > sym_center[1]:
            col_iter = np.arange(sym_center[1],sym_corner[1]+1,1)
        else:
            col_iter = np.arange(sym_center[1],sym_corner[1]-1,-1)

        core_dict={}
        for irow in row_iter:
            for icol in col_iter:
                if icol>irow:
                    continue
                dict_value={'Symmetric_Assemblies':[],
                            'Value': None}
                if (irow,icol) == sym_center:
                    pass
                elif icol == sym_vertical[1] and irow != sym_center[0]:                 
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == idx) & (core_id[:,:,1] == -idy))
                    idxy_2= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    idxy_3= np.where((core_id[:,:,0] == idx) & (core_id[:,:,1] == idy))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0], core_map[idxy_2][0], core_map[idxy_3][0]]
                elif icol == irow and irow != sym_center[0]:
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    idxy_2= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == -idx))
                    idxy_3= np.where((core_id[:,:,0] == idy) & (core_id[:,:,1] == -idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0], core_map[idxy_2][0], core_map[idxy_3][0]]
                else:
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == -idx) & (core_id[:,:,1] == -idy))
                    idxy_2= np.where((core_id[:,:,0] == idx) & (core_id[:,:,1] == -idy))
                    idxy_3= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    idxy_4= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == -idx))
                    idxy_5= np.where((core_id[:,:,0] == idx) & (core_id[:,:,1] == idy))
                    idxy_6= np.where((core_id[:,:,0] == -idx) & (core_id[:,:,1] == idy))
                    idxy_7= np.where((core_id[:,:,0] == idy) & (core_id[:,:,1] == -idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0], core_map[idxy_2][0], core_map[idxy_3][0], core_map[idxy_4][0],
                                                          core_map[idxy_5][0], core_map[idxy_6][0], core_map[idxy_7][0]]
                core_dict[core_map[irow,icol]] = dict_value
                fuel_dict = self.extract_fuel(core_dict)
        return(core_dict,fuel_dict)

    def extract_fuel(self, core_dict):
        """
        Extracts the unique fuel assemblies from the core in a dictionary.

        Parameters: 
           - core_dict: a core dictionary including all the geometrical parameters.

        Written by Gregory Delipei 7/12/2022
        """
        fuel_dict={}
        for key, value in core_dict.items():
            if key is None:
                continue
            elif key[0]=="R":
                continue
            else:
                fuel_dict[key]=value
        return(fuel_dict)

    def random_design(self):
        """
        Generates a random design following the constraints in the inventory.

        Parameters: None

        Written by Gregory Delipei 7/13/2022
        """

        # Initialization

        avail_locations=list(self.core_dict['fuel'].keys())
        assembly_types = list(self.core_dict['Inventory'].keys())

        for iass in assembly_types:
            self.core_dict['Inventory'][iass]['In_Desing'] = 0

        assembly_types_group = copy.deepcopy(assembly_types)
        avail_locations_group = copy.deepcopy(avail_locations)
        maxiter=10000 # maximum iterations to avoid infinite loop.
        nfuel, nfuel_sym, nrefl, nrefl_sym = self.compute_fa_number()
        total_fuel = nfuel
        total=0

        # Select randomly the fuel assemblies with exact limits in the inventory groups
        for key, value in self.core_dict['Inventory_Groups'].items():
            total_group=0
            if value['Limit']=='Exact':
                niter=0
                while total_group != value['Limit_Value'] and niter<maxiter:
                    avail_choices = []
                    for iloc in avail_locations_group:
                        for iass in value['Values']:
                            proposed_choice = (iloc, iass)
                            symmetry_multiplier = len(self.core_dict['fuel'][iloc]['Symmetric_Assemblies'])+1
                            if (total_group + symmetry_multiplier <= value['Limit_Value']) and (self.core_dict['Inventory'][iass]['In_Design'] <= self.core_dict['Inventory'][iass]['Max_Limit']-symmetry_multiplier):
                                avail_choices.append(proposed_choice)
                    # Re-iterate if the selected random filling strategy cannot meet the inventory limits.
                    if len(avail_choices)==0:
                        total_group=0
                        niter +=1
                        avail_locations_group = copy.deepcopy(avail_locations)
                        for iass in assembly_types_group:
                            self.core_dict['Inventory'][iass]['In_Design'] = 0
                        print(f"New Exact Filling Strategy - {niter}")
                        continue

                    sampled_choice = random.choice(avail_choices)
                    sloc = sampled_choice[0]
                    sass = sampled_choice[1]
                    self.core_dict['fuel'][sloc]['Value']=sass
                    self.core_dict['core'][sloc]['Value']=sass
                    symmetry_multiplier = len(self.core_dict['fuel'][sloc]['Symmetric_Assemblies'])+1
                    self.core_dict['Inventory'][sass]['In_Design']+= symmetry_multiplier
                    avail_locations_group.remove(sloc)
                    total_group+=symmetry_multiplier

                # Update the remaining available quantities for the next inventory groups
                for iass in value['Values']:
                    assembly_types_group.remove(iass)
                avail_locations = copy.deepcopy(avail_locations_group)
                assembly_types=copy.deepcopy(assembly_types_group)
                total+=total_group
        
        # Select randomly the fuel assemblies without exact limits in the inventory groups
        niter=0
        while total != total_fuel and niter<maxiter:
            avail_choices = []
            for iloc in avail_locations:
                for key, value in self.core_dict['Inventory_Groups'].items(): 
                    if value['Limit']!='Exact':
                        subtotal = 0
                        for iass in value["Values"]:
                            subtotal+=self.core_dict['Inventory'][iass]['In_Design']
                        for iass in value["Values"]:
                            proposed_choice = (iloc, iass)
                            symmetry_multiplier = len(self.core_dict['fuel'][iloc]['Symmetric_Assemblies'])+1
                            if (self.core_dict['Inventory'][iass]['In_Design'] <= self.core_dict['Inventory'][iass]['Max_Limit']-symmetry_multiplier) and (subtotal <=value['Limit_Value']-symmetry_multiplier):
                                avail_choices.append(proposed_choice)
      
            # Re-iterate if the selected random filling strategy cannot meet the inventory limits.
            if len(avail_choices)==0:
                total=total_group
                niter +=1
                avail_locations = copy.deepcopy(avail_locations_group)
                for iass in assembly_types:
                    self.core_dict['Inventory'][iass]['In_Desing'] = 0
                print(f"New Filling Strategy - {niter}")
                continue
            sampled_choice = random.choice(avail_choices)
            sloc = sampled_choice[0]
            sass = sampled_choice[1]
            self.core_dict['fuel'][sloc]['Value']=sass
            self.core_dict['core'][sloc]['Value']=sass
            symmetry_multiplier = len(self.core_dict['fuel'][sloc]['Symmetric_Assemblies'])+1
            self.core_dict['Inventory'][sass]['In_Design']+= symmetry_multiplier
            avail_locations.remove(sloc)
            total+=symmetry_multiplier

        return
    
    def action(self,act):
        """
        Performs an action on the current design and updates it.

        Parameters: 
            - act: Dictionary with the action options.

        Written by Gregory Delipei 7/14/2022
        """
        avail_actions = self.get_actions()
        action_type = act['Type']
        action_location = act['Location']
        action = act['Value']

        if action in avail_actions[action_type][action_location]:
            if action_type =='Exchange':
                loc_value = self.core_dict['core'][action_location]['Value']
                action_value = self.core_dict['core'][action]['Value']
                self.core_dict['core'][action_location]['Value'] = action_value
                self.core_dict['fuel'][action_location]['Value'] = action_value
                self.core_dict['core'][action]['Value'] = loc_value
                self.core_dict['fuel'][action]['Value'] = loc_value
            elif action_type=='Change':
                loc_value = self.core_dict['core'][action_location]['Value']
                loc_symmetry=len(self.core_dict['fuel'][action_location]['Symmetric_Assemblies'])+1
                self.core_dict['core'][action_location]['Value'] = action
                self.core_dict['fuel'][action_location]['Value'] = action
                self.core_dict['Inventory'][loc_value]['In_Design']-=loc_symmetry
                self.core_dict['Inventory'][action]['In_Design']+=loc_symmetry
        else:
            raise ValueError(
                f"The selected action is not valid."
            )
        return

    def mapaction(self,mact):
        """
        Performs an action on the current design and updates it.

        Parameters: 
            - act: Dictionary with the action options.

        Written by Gregory Delipei 7/14/2022
        """
        avail_actions = self.get_actions()
        action_mvalue = mact['Value']
        action_location = mact['Location']
        loc_actions=avail_actions['Map'][action_location]
        for key,value in loc_actions.items():
            bounds = value['Bounds']
            if bounds[0]<=action_mvalue<bounds[1]:
                action_type = value['Type']
                action = value['Value']
            if action_mvalue==bounds[1]==1:
                action_type = value['Type']
                action = value['Value']
        
        if action in avail_actions[action_type][action_location]:
            if action_type =='Exchange':
                loc_value = self.core_dict['core'][action_location]['Value']
                action_value = self.core_dict['core'][action]['Value']
                self.core_dict['core'][action_location]['Value'] = action_value
                self.core_dict['fuel'][action_location]['Value'] = action_value
                self.core_dict['core'][action]['Value'] = loc_value
                self.core_dict['fuel'][action]['Value'] = loc_value
            elif action_type=='Change':
                loc_value = self.core_dict['core'][action_location]['Value']
                loc_symmetry=len(self.core_dict['fuel'][action_location]['Symmetric_Assemblies'])+1
                self.core_dict['core'][action_location]['Value'] = action
                self.core_dict['fuel'][action_location]['Value'] = action
                self.core_dict['Inventory'][loc_value]['In_Design']-=loc_symmetry
                self.core_dict['Inventory'][action]['In_Design']+=loc_symmetry
        else:
            raise ValueError(
                f"The selected action is not valid."
            )
        return

    def get_actions(self):
        """
        Extracts all possible actions in a dictionary.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """

        # Compute exchange type of actions
        exchange_act = {}
        for key, value in self.core_dict["fuel"].items():
            avail_choices=[]
            key_symmetry = len(self.core_dict['fuel'][key]['Symmetric_Assemblies'])+1
            for key_ex,value_ex in  self.core_dict["fuel"].items():
                key_ex_symmetry = len(self.core_dict['fuel'][key_ex]['Symmetric_Assemblies'])+1
                if key_symmetry == key_ex_symmetry:
                    selected_choice=key_ex
                    avail_choices.append(selected_choice)
            exchange_act[key]=avail_choices

        # Compute change type of actions
        change_act = {}
        for key, value in self.core_dict["fuel"].items():
            avail_choices=[]
            loc_symmetry = len(self.core_dict['fuel'][key]['Symmetric_Assemblies'])+1
            loc_value = self.core_dict['fuel'][key]['Value']
            loc_group = self.get_inventory_group(loc_value)
            loc_group_limit = self.core_dict['Inventory_Groups'][loc_group]['Limit']
            for key_group,value_group in  self.core_dict['Inventory_Groups'].items(): 
                key_group_limit = self.core_dict['Inventory_Groups'][key_group]['Limit']
                for iass in value_group["Values"]:
                    if loc_group_limit=='Exact' and key_group==loc_group:
                        iass_limit = self.core_dict['Inventory'][iass]['Max_Limit']
                        iass_indesign = self.core_dict['Inventory'][iass]['In_Design']
                        if loc_symmetry + iass_indesign <= iass_limit:
                            selected_choice = iass
                            avail_choices.append(selected_choice)
                    elif loc_group_limit=='Max' and key_group_limit=='Max' and key_group!=loc_group:
                        iass_limit = self.core_dict['Inventory'][iass]['Max_Limit']
                        iass_indesign = self.core_dict['Inventory'][iass]['In_Design']
                        group_limit = value_group['Limit_Value']
                        group_indesign = self.get_group_indesign(key_group)
                        if (loc_symmetry + iass_indesign <= iass_limit) and (loc_symmetry + group_indesign <= group_limit):
                            selected_choice = iass
                            avail_choices.append(selected_choice)
                    elif loc_group_limit=='Max' and key_group_limit=='Max' and key_group==loc_group:
                        iass_limit = self.core_dict['Inventory'][iass]['Max_Limit']
                        iass_indesign = self.core_dict['Inventory'][iass]['In_Design']
                        if (loc_symmetry + iass_indesign <= iass_limit):
                            selected_choice = iass
                            avail_choices.append(selected_choice)
            change_act[key]=avail_choices

        # Create mapping from [0,1] to action
        map_act = {}
        for key, value in self.core_dict["fuel"].items():
            nex_act = len(exchange_act[key])
            nch_act = len(change_act[key])
            nact = nex_act + nch_act
            act_bounds = np.linspace(self.action_lower,self.action_upper,nact+1)
            mdict={}
            it=0
            for i in range(nch_act):
                it+=1
                adict={}
                adict['Bounds'] = np.array([act_bounds[it-1],act_bounds[it]])
                adict['Type'] = 'Change'
                adict['Value'] = change_act[key][i]
                mdict['Act'+str(it)] = adict
            for i in range(nex_act):
                it+=1
                adict={}
                adict['Bounds'] = np.array([act_bounds[it-1],act_bounds[it]])
                adict['Type'] = 'Exchange'
                adict['Value'] = exchange_act[key][i]
                mdict['Act'+str(it)] = adict
            map_act[key]=mdict
                
        act_dict={'Exchange': exchange_act,
                  'Change': change_act,
                  'Map': map_act}
        return(act_dict)

    def get_mapstate(self):
        """
        Gets the current state in a normalized format.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """
        mstate=np.zeros(len(self.core_dict['fuel'].keys()),dtype=np.int8)
        it=0
        for key, value in self.core_dict['fuel'].items():
            mstate[it]=self.cmap[value['Value']]
            it+=1
        return(mstate)

    def get_inventory_group(self,iass):
        """
        Get in which group an assembly belongs to.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """
        igroup = None
        for key,value in self.core_dict['Inventory_Groups'].items():
            if iass in value['Values']:
                igroup = key
        return(igroup)
    
    def get_group_indesign(self,group):
        """
        Get in which group an assembly belongs to.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """
        sum_in = 0
        for iass in self.core_dict['Inventory_Groups'][group]['Values']:
            sum_in += self.core_dict['Inventory'][iass]['In_Design']
        return(sum_in)

    def plot_design(self,filepath):
        """
        Plot current loading pattern design.

        Parameters: None

        Written by Gregory Delipei 7/13/2022
        """
        color_fill = ['maroon','red','darkorange','limegreen','turquoise','pink','purple','plum','teal']
        nfa = 1
        tags=[]
        for key in self.core_dict['Inventory'].keys():
            if self.core_dict['Inventory'][key]['In_Design'] > 0:
                nfa+=1
                tags.append(key)
        ass_pitch = 21.21      

        plt.rcParams.update({'font.size': 4})
        fig=plt.figure()
        plt.axes()

        value_map = copy.deepcopy(self.core_dict['core_map'])
        value_map = value_map.astype('<U12')
        for key, value in self.core_dict['core'].items():
            value_map[np.where(self.core_dict['core_map']==key)] = value['Value']
            for isym in value['Symmetric_Assemblies']:
                value_map[np.where(self.core_dict['core_map']==isym)] = value['Value']

        for i in range(17):
            for j in range(17):
                ass_type=value_map[i,j]
                yloc=self.core_dict['core_id'][i,j][0]
                xloc=self.core_dict['core_id'][i,j][1]
                yid = yloc*ass_pitch
                xid = xloc*ass_pitch
                if ass_type == 'None':
                    continue
                else:
                    ass_color = color_fill[tags.index(ass_type)]
                    rectangle = plt.Rectangle((xid,yid),ass_pitch, ass_pitch,fc=ass_color,ec='grey')
                    plt.gca().add_patch(rectangle)
                    plt.text(xid+5,yid+9,self.core_dict['core_map'][i,j])


        plt.rcParams.update({'font.size': 8})
        rectangle = plt.Rectangle((12*ass_pitch,8*ass_pitch),0.3*ass_pitch,0.2*ass_pitch,1,fc="White")
        plt.gca().add_patch(rectangle)
        for i in range(len(tags)):    
            rectangle = plt.Rectangle((9.0*ass_pitch,8*ass_pitch-i*ass_pitch),0.4*ass_pitch,0.3*ass_pitch,1,fc=color_fill[i])
            plt.gca().add_patch(rectangle)
            plt.text(9.5*ass_pitch,8*ass_pitch-i*ass_pitch-0.03*ass_pitch,tags[i])

        plt.axis('scaled')
        plt.tick_params(left = False, right = False , labelleft = False ,
                        labelbottom = False, bottom = False)

        plt.savefig(filepath,bbox_inches='tight',dpi=300) 
        plt.close(fig)

    def compute_fa_number(self):
        """
        Computes the total number of fuel/reflector assemblies in the core with and without symmetry.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """
        nfuel=0
        nfuel_sym=0
        nrefl = 0
        nrefl_sym = 0
        for key, value in self.core_dict['core'].items():
            symmetry_multiplier = len(self.core_dict['core'][key]['Symmetric_Assemblies'])+1
            if key is None:
                continue
            elif key[0]=='R':
                nrefl_sym+=1
                nrefl+=symmetry_multiplier
            else:
                nfuel_sym+=1
                nfuel+=symmetry_multiplier
        return(nfuel,nfuel_sym,nrefl,nrefl_sym)

        return
    
    def set_state(self,state):
        
        for key,value in self.core_dict['Inventory'].items():
            nvalue = value['In_Design']=0
            self.core_dict['Inventory'][key] = value

        for key, value in state.items():
            symmetry_multiplier = len(self.core_dict['fuel'][key]['Symmetric_Assemblies'])+1
            self.core_dict['fuel'][key]['Value']=value
            self.core_dict['core'][key]['Value']=value
            self.core_dict['Inventory'][value]['In_Design']+=symmetry_multiplier
        return

    def get_state(self):
        state={}
        for key, value in self.core_dict['fuel'].items():
            state[key]=value['Value']
        return(state)
    
    def genes_in_group(self,chromosome_map,group_name):
        """
        Returns a list of the genes in the chosen group
        """
        gene_list = []
        for gene in chromosome_map:
            if gene == 'symmetry_list':
                pass
            else:
                if group_name == chromosome_map[gene]['gene_group']:
                    gene_list.append(gene)

        return gene_list

    def is_gene_ok(self,chromosome_map,gene,space):
        """
        Checks if the gene is allowed in the desired location
        """
        gene_is_ok = True
        if not chromosome_map[gene]['map'][space]:
            gene_is_ok = False
        if space in chromosome_map['symmetry_list']:
            if self.my_group[chromosome_map[gene]['gene_group']] <= 1:
                gene_is_ok = False
        else:
            if not self.my_group[chromosome_map[gene]['gene_group']]:
                gene_is_ok = False
        if 'unique' in chromosome_map[gene]:
            if gene in self.genome:
                gene_is_ok = False

        return gene_is_ok

    def generate_initial(self,chromosome_map):
        """
        Generates the initial solutions to the optimization problem.

        Parameters: 
            chromosome_map: Dictionary
                The genome portion of the dictionary settings file. 

        Written by Brian Andersen. 1/9/2020
        """
        chromosome_length = None
        chromosome_list = list(chromosome_map.keys())
        if 'symmetry_list' in chromosome_list:
            chromosome_list.remove('symmetry_list')

        for chromosome in chromosome_list:
            if chromosome_length is None:
                chromosome_length = len(chromosome_map[chromosome]['map'])
            elif len(chromosome_map[chromosome]['map']) == chromosome_length:
                pass
            else:
                raise ValueError("Chromosome Maps are of unequal length")

        self.genome = []                                #Unburnt assemblies
        for i in range(chromosome_length):              #better off just being implemented
            no_gene_found = True                        #as a single gene.
            while no_gene_found:
                gene = random.choice(chromosome_list)
                if chromosome_map[gene]['map'][i]:
                    self.genome.append(gene)
                    no_gene_found = False
        
    def generate_initial_fixed(self,chromosome_map,gene_groups):
        """
        Generates initial solution when only specific number of assemblies
        may be used.

        Written by Brian Andersen 3/15/2020
        """
        chromosome_length = None
        chromosome_list = list(chromosome_map.keys())
        if 'symmetry_list' in chromosome_list:
            chromosome_list.remove('symmetry_list')

        for chromosome in chromosome_list:
            if chromosome_length is None:
                chromosome_length = len(chromosome_map[chromosome]['map'])
            elif len(chromosome_map[chromosome]['map']) == chromosome_length:
                pass
            else:
                raise ValueError("Chromosome Maps are of unequal length")

        no_valid_solution = True
        while no_valid_solution:
            no_valid_solution = False
            my_group = copy.deepcopy(gene_groups)
            self.genome = [None]*chromosome_length
            for i in range(chromosome_length):
                no_gene_found = True
                attempt_counter = 0
                while no_gene_found:
                    gene = random.choice(chromosome_list)
                    if 'unique' in chromosome_map[gene]:
                        if chromosome_map[gene]['unique']:
                            if gene in self.genome:
                                pass
                            else:
                                #This else loop activates if the gene is labeled unique but is not used. 
                                if chromosome_map[gene]['map'][i] == 1:
                                    if i in chromosome_map['symmetry_list']:
                                        if my_group[chromosome_map[gene]['gene_group']] > 1:
                                            self.genome[i] = gene
                                            no_gene_found = False
                                            my_group[chromosome_map[gene]['gene_group']] -= 2
                                    else:
                                        if my_group[chromosome_map[gene]['gene_group']] > 0:
                                            self.genome[i] = gene
                                            no_gene_found = False
                                            my_group[chromosome_map[gene]['gene_group']] -= 1            
                        else:
                            #adding unique loop above this code
                            if chromosome_map[gene]['map'][i] == 1:
                                if i in chromosome_map['symmetry_list']:
                                    if my_group[chromosome_map[gene]['gene_group']] > 1:
                                        self.genome[i] = gene
                                        no_gene_found = False
                                        my_group[chromosome_map[gene]['gene_group']] -= 2
                                else:
                                    if my_group[chromosome_map[gene]['gene_group']] > 0:
                                        self.genome[i] = gene
                                        no_gene_found = False
                                        my_group[chromosome_map[gene]['gene_group']] -= 1
                    else:
                        #adding unique loop above this code
                        if chromosome_map[gene]['map'][i] == 1:
                            if i in chromosome_map['symmetry_list']:
                                if my_group[chromosome_map[gene]['gene_group']] > 1:
                                    self.genome[i] = gene
                                    no_gene_found = False
                                    my_group[chromosome_map[gene]['gene_group']] -= 2
                            else:
                                if my_group[chromosome_map[gene]['gene_group']] > 0:
                                    self.genome[i] = gene
                                    no_gene_found = False
                                    my_group[chromosome_map[gene]['gene_group']] -= 1
                    attempt_counter += 1
                    if attempt_counter == 100:
                        no_gene_found = False
                        no_valid_solution = True

    def new_generate_initial_fixed(self,chromosome_map,gene_groups):
        """
        Generates initial solution when only speciific number of assemblies may be used.

        Written by Brian Andersen 3/15/2020. Last edited 11/20/2020
        """
        #above here is the old code
        chromosome_length = None
        chromosome_list = list(chromosome_map.keys())
        if 'symmetry_list' in chromosome_list:
            chromosome_list.remove('symmetry_list')

        for chromosome in chromosome_list:
            if chromosome_length is None:
                chromosome_length = len(chromosome_map[chromosome]['map'])
            elif len(chromosome_map[chromosome]['map']) == chromosome_length:
                pass
            else:
                raise ValueError("Chromosome Maps are of unequal length")

        no_genome_found = True
        while no_genome_found:
            attempts = 0
            self.my_group = copy.deepcopy(gene_groups)
            self.genome = [None]*chromosome_length
            unfilled_spaces = list(range(chromosome_length))
            while unfilled_spaces:  
                space_number = random.randint(0,len(unfilled_spaces)-1)
                group_name = None
                while not group_name:
                    random_group = random.choice(list(self.my_group.keys()))
                    if self.my_group[random_group] > 0:
                        group_name = random_group
                available_gene_list = self.genes_in_group(chromosome_map,group_name)
                space = unfilled_spaces[space_number]
                gene = random.choice(available_gene_list)
                gene_is_ok = self.is_gene_ok(chromosome_map,gene,space)
                if gene_is_ok:
                    self.genome[space] = gene
                    unfilled_spaces.remove(space)
                    if space in chromosome_map['symmetry_list']:
                        self.my_group[chromosome_map[gene]['gene_group']] -= 2
                    else:
                        self.my_group[chromosome_map[gene]['gene_group']] -= 1             
                else:
                    attempts += 1
                if attempts == 100:
                    break

            bad_gene_list = []
            for i,gene in enumerate(self.genome):
                if not gene:
                    bad_gene_list.append(i)

            if not bad_gene_list:
                no_genome_found = False                

    def get_clength(self,efpd,boron,keff):
        if boron[-1]==0.1:
            eoc1_ind = 0
            eco2_ind = len(efpd)
            for i in range(len(efpd)):
                if boron[i] > 0.1 and boron[i+1] == 0.1:
                    eoc1_ind = i
                    eco2_ind = i+1
            dbor = abs(boron[eoc1_ind-1]-boron[eoc1_ind])
            defpd = abs(efpd[eoc1_ind-1]-efpd[eoc1_ind])
            def_dbor = defpd/dbor
            eoc = efpd[eoc1_ind] + def_dbor*(boron[eoc1_ind]-0.1)
        elif boron[-1]==boron[0]==1800.0:
            drho_dcb=10 
            drho1 = (keff[-2]-1.0)*10**5
            dcb1 = drho1/drho_dcb
            cb1= boron[-2] + dcb1
            drho2 = (keff[-1]-1.0)*10**5
            dcb2 = drho2/drho_dcb
            cb2= boron[-1] + dcb2
            dbor = abs(cb1-cb2)
            defpd = abs(efpd[-2]-efpd[-1])
            def_dbor = defpd/dbor
            eoc = efpd[-1] + def_dbor*(cb2-0.1)
        else:
            dbor = abs(boron[-2]-boron[-1])
            defpd = abs(efpd[-2]-efpd[-1])
            def_dbor = defpd/dbor
            eoc = efpd[-1] + def_dbor*(boron[-1]-0.1)
        return(eoc)

    def get_pin_power(self,filepath):
        start = time.time()
        print('Reading of Pin Powers')
        npx=17
        npy=17
        npin = npx*npy
        nbu = 17
        nz=16
        nasb = self.compute_nasb()
        pp_mat = np.zeros((nbu,nasb,nz,npin))
        for iasb in range(nasb):
            pinfile = filepath + ".parcs_pin" + str(iasb+1).zfill(3)
            ofile = open(pinfile, "r")
            filestr = ofile.read()
            ofile.close()
            asbstr = filestr.split('  Case:')
            for i in range(1,len(asbstr)):
                asb_line =asbstr[i].split('\n')
                ibu=int(asb_line[0][0:4])-1
                iz_val = int(asb_line[0][66:68])
                if iz_val == 0:
                    continue
                else:
                    iz = iz_val-2
                    pp_str = asb_line[2:2+npy]
                    for iy in range(npy):
                        for ix in range(npx):
                            pp_id = iy*npx + ix 
                            try:
                                pp_mat[ibu,iasb,iz,pp_id] = float(pp_str[iy][(7*ix + 8):(7*ix + 14)])
                            except:
                                print("Non physical peaking factors")
                                pp_mat[ibu,iasb,iz,pp_id] = 10.0

        end = time.time()
        print('Pin Power Duration = {} s'.format(end-start))
        return(pp_mat)

    def get_asb_power(self,filepath):
        start = time.time()
        print('Reading of Assembly Powers')
        ofile = open(filepath+".parcs_dep", "r")
        filestr = ofile.read()
        ofile.close()
        bustr=filestr.split(" RPF 3D MAP")
        nbu= len(bustr)-1
        nz_str = bustr[0].split(' RPF 1D MAP')[1].split('\n')
        nrefl=2
        nz = len(nz_str)-4-nrefl
        ztag = np.arange(2,nz+1 + 1)
        nasb = self.compute_nasb()
        asb_mat = np.zeros((nbu,nasb,nz))
        for ibu in range(nbu):
            ibustr = bustr[ibu+1].split(' EXP 2D MAP')[0]
            asb_str = ibustr.split(' k lb')
            iasb=0
            for ik in range(1,len(asb_str)):
                asb_line=asb_str[ik].split('\n')
                for iz in range(1,len(asb_line)):
                    asb_val=asb_line[iz].split()
                    if len(asb_val)>0:
                        if int(asb_val[0]) in ztag:
                            zid = int(asb_val[0])-2
                            asb_count = 0
                            for ia in range(1,len(asb_val)):
                                val = float(asb_val[ia])
                                if  val !=0.0:
                                    asb_id = iasb + asb_count
                                    asb_mat[ibu,asb_id,zid]=val
                                    asb_count+=1
                                else:
                                    continue
                    else:
                        continue
                iasb += asb_count
        end = time.time()
        print('Assembly Power Duration = {} s'.format(end-start))
        return(asb_mat)

    def get_lcoe(self):
        
        cycle_param={'EFPD': self.parameters['cycle_length']['value'],
                    'Batches': 3,
                    'Thermal_Power': self.power,
                    'Efficiency': 0.33,
                    'Fuel_Assemblies': self.number_assemblies}

        lcoe_param={'Discount_Rate': 0.07,
                    'Uranium_Ore_Price': 80,
                    'Conversion_Price': 10,
                    'Enrichment_Price': 160,
                    'Fabrication_Price': 250,
                    'Uranium_Ore_Loss': 0.002,
                    'Conversion_Loss': 0.002,
                    'Enrichment_Loss': 0.002,
                    'Fabrication_Loss': 0.002,
                    'Enrichment_Feed': 0.00711,
                    'Enrichment_Tail': 0.003,
                    'Storage_Price': 200,
                    'Disposal_Price': 463,
                    'Uranium_Ore_Time': -2.0,
                    'Conversion_Time': -1.5,
                    'Enrichment_Time': -1.0,
                    'Fabrication_Time': -0.5,
                    'Storage_Time': 5.0+cycle_param['EFPD']*cycle_param['Batches']/365.25,
                    'Disposal_Time': cycle_param['EFPD']*cycle_param['Batches']/365.25}

        unique_fa =  np.unique(list(self.full_core.values()))
        asb_param = {}
        for i in range(len(unique_fa)):
            nfa = list(self.full_core.values()).count(unique_fa[i])
            enr = float(unique_fa[i][2:5])/10000
            asb_dict = {'Number': nfa,
                        'Fuel_Rods': 264,
                        'Fuel_Radius': 0.41,
                        'Fuel_Height': 365.76,
                        'Enrichment': enr,
                        'Fuel_Density': 10.23,
                        'Fabrication_Price': 250
                        }
            asb_param[unique_fa[i]]=asb_dict

        lcoe, bu, asb_cost = LCOE(cycle_param,lcoe_param, asb_param)
        asb_cost_dict = {}
        for i in range(len(unique_fa)):
            asb_cost_dict[unique_fa[i]]=asb_cost[i]

        return((lcoe, bu, asb_cost_dict))

    def get_results(self,filepath,pin_power=False):
        efpd=[]
        boron =[]
        fq=[]
        fdh=[]
        keff = []
        read_bool  = False
        ofile = open(filepath + ".parcs_dpl", "r")
        filestr = ofile.read()
        ofile.close()
        res_str = filestr.split('===============================================================================')
        res_str = res_str[1].split('-------------------------------------------------------------------------------')
        res_str = res_str[0].split('\n')
        for i in range(2, len(res_str)-1):
            res_val=res_str[i].split()
            efpd.append(float(res_val[9]))
            boron.append(float(res_val[14]))
            keff.append(float(res_val[2]))
            fq.append(float(res_val[7]))
            fdh.append(float(res_val[6]))
        res = {}
        self.parameters["cycle_length"]['value'] = self.get_clength(efpd,boron,keff)       
        self.parameters["PinPowerPeaking"]['value'] = max(fq)
        self.parameters["FDeltaH"]['value'] = max(fdh)
        self.parameters["max_boron"]['value'] = max(boron)
        if self.parameters["max_boron"]['value'] == 1800.0:
            max_boron =0
            for i in range(len(boron)):
                if boron[i]== 1800.0:
                    drho_dcb=10 
                    drho = (keff[i]-1.0)*10**5
                    dcb = drho/drho_dcb
                    mboron = 1800.0+dcb
                    if mboron > max_boron:
                        max_boron = mboron
            self.parameters["max_boron"]['value'] = max_boron
            
        lcoe, discharge_bu, asb_cost = self.get_lcoe()
        self.additional_parameters= {}
        self.additional_parameters["LCOE"] = lcoe
        self.additional_parameters["Discharge_Burnup"]=discharge_bu
        self.additional_parameters["Assemblies_Costs"] = asb_cost
        if pin_power:
            zh = np.array([15.24, 10.16, 5.08, 30.48, 30.48, 30.48, 30.48, 30.48,
                        30.48, 30.48, 30.48, 30.48, 30.48, 5.08, 10.16, 15.24])
            asb_mat=self.get_asb_power(filepath)
            pp_mat = self.get_pin_power(filepath)
            fq_asb = np.max(asb_mat)
            fdh_asb = 0
            for ibu in range(asb_mat.shape[0]):
                for iasb in range(asb_mat.shape[1]):
                    fdh_i = np.dot(asb_mat[ibu,iasb,:],zh)/np.sum(zh)
                    if fdh_i > fdh_asb:
                        fdh_asb = fdh_i
            fq_pp = 0
            fdh_pp = 0
            fq_id = np.array([0,0])
            fdh_id = np.array([0,0])
            for ibu in range(asb_mat.shape[0]):
                for iasb in range(asb_mat.shape[1]):
                    iasb_mat = np.zeros((pp_mat.shape[2],pp_mat.shape[3]))
                    for iz in range(pp_mat.shape[2]):
                        iasb_mat[iz,:]=pp_mat[ibu,iasb,iz,:]
                    fq_i = np.max(iasb_mat)
                    if fq_i > fq_pp:
                        fq_pp = fq_i
                        fq_id[0]=ibu 
                        fq_id[1]=iasb
                    for ip in range(pp_mat.shape[3]):
                        fdh_i = np.dot(iasb_mat[:,ip],zh)/np.sum(zh)
                        if fdh_i > fdh_pp:
                            fdh_pp = fdh_i
                            fdh_id[0]=ibu 
                            fdh_id[1]=iasb
            self.parameters["PinPowerPeaking"]['value'] = fq_pp
            self.parameters["FDeltaH"]['value'] = fdh_pp

    def get_quarter_lattice(self):
            """
            Generates the 17x17 quarter core lattice.

            Parameters: None
        
            Written by Gregory Delipei 7/24/2022
            """
            core_map = self.core_dict['core_map']
            core_id = self.core_dict['core_id']
            nx = int(np.ceil(len(core_map[0])/2))
            ny = int(np.ceil(len(core_map)/2))
            quarter_core = np.zeros((ny,nx), dtype='<U8')
            for y in range(ny):
                for x in range(nx):
                    val =core_map[ny-1+y,nx-1+x]
                    if val is None:
                        val = "00"
                    quarter_core[y,x] = val
            return(quarter_core)

    def get_full_lattice(self):
            """
            Generates the 17x17 quarter core lattice.

            Parameters: None
        
            Written by Gregory Delipei 7/24/2022
            """
            core_map = self.core_dict['core_map']
            core_id = self.core_dict['core_id']
            nx = int(len(core_map[0]))
            ny = int(len(core_map))
            quarter_core = np.zeros((ny,nx), dtype='<U8')
            for y in range(ny):
                for x in range(nx):
                    val =core_map[y,x]
                    if val is None:
                        val = "00"
                    quarter_core[y,x] = val
            return(quarter_core)

    def compute_nasb(self):
        nfa=0
        for x in range(self.core_lattice.shape[0]):
            for y in range(self.core_lattice.shape[1]):
                loc = self.core_lattice[x,y]
                if loc != "00 " and loc != "10 ":
                    nfa+=1
                else:
                    pass
        return(nfa)

    def evaluate(self):
            """
            Creates the input deck, runs the calculation and retrieves the results and the cost.

            Parameters: 
            loc: String - Directory of execution
            fname: String - File name

            Written by Gregory Delipei 7/29/2022
            """

            # Create PARCS INPUT DECK

            pwd = Path(os.getcwd())

            if not os.path.exists(self.name):
                os.makedirs(self.name)
            else:
                shutil.rmtree(self.name, ignore_errors=True)
                os.makedirs(self.name)
            
            cdir = self.library
            shutil.copyfile(cdir + '/' + 'boc_exp_quart193_18.dep', self.name +"/" + 'boc_exp.dep')
            os.chdir(self.name)
 
            fuel_locations = list(self.core_dict['fuel'].keys())
            self.genome_dict = {}

            for i in range(len(self.genome)):
                self.genome_dict[fuel_locations[i]]=self.genome[i]
                self.core_dict['fuel'][fuel_locations[i]]['Value']=self.genome[i]
                self.core_dict['core'][fuel_locations[i]]['Value']=self.genome[i]

            self.full_core = self.get_full_core()
            if self.map_size == 'quarter':
                self.core_lattice = self.get_quarter_lattice()
            else:
                self.core_lattice = self.get_full_lattice()

            xs_array = np.zeros((self.core_lattice.shape[0],self.core_lattice.shape[1]), dtype='<U20')
            pincal_loc = np.zeros((self.core_lattice.shape[0],self.core_lattice.shape[1]))
            for x in range(self.core_lattice.shape[0]):
                for y in range(self.core_lattice.shape[1]):
                    loc = self.core_lattice[x,y]
                    if loc != "00" and loc[0] != "R":
                        self.core_lattice[x,y] = self.core_dict['Inventory'][self.full_core[loc]]['Tag']
                        xs_array[x,y] = self.core_dict['Inventory'][self.full_core[loc]]['Cross_Section']
                        pincal_loc[x,y]=1
                    elif loc[0] == "R":
                        self.core_lattice[x,y] = "10 "
                        xs_array[x,y] = None
                        pincal_loc[x,y]=0
                    elif loc == "00":
                        self.core_lattice[x,y] = "00 "
                        xs_array[x,y] = None
                        pincal_loc[x,y]=np.nan

            xs_unique = np.unique(xs_array)
            xs_unique = np.delete(xs_unique, np.argwhere(xs_unique == 'None'))

            tag_unique = copy.deepcopy(xs_unique)
            xs_ref = np.arange(5,5+len(xs_unique)) # 1-3 for reflectors and 4 for blankets
            for key,value in self.core_dict["Inventory"].items():
                for i in range(xs_unique.shape[0]):
                    if value['Cross_Section']==xs_unique[i]:
                        tag_unique[i]=value['Tag']
            fname = 'solution'
            filename = fname + '.inp'
            with open(filename,"w") as ofile:             
                ofile.write("!******************************************************************************\n")
                ofile.write('CASEID {}  \n'.format(fname))
                ofile.write("!******************************************************************************\n\n")

            with open(filename,"a") as ofile:             
                ofile.write("CNTL\n")
                ofile.write("     RUN_OPTS F T F F\n")
                ofile.write("     TH_FDBK    T\n")
                ofile.write("     INT_TH     T -1\n")
                ofile.write("     CORE_POWER 100.0\n")
                ofile.write("     CORE_TYPE  PWR\n")
                ofile.write("     PPM        1000 1.0 1800.0 10.0\n")
                ofile.write("     DEPLETION  T  1.0E-5 T\n")
                ofile.write("     TREE_XS    T  {} T  T  F  F  T  F  T  F  T  F  T  T  T  F \n".format(int(len(xs_unique)+4)))
                ofile.write("     BANK_POS   100 100 100 100 100 100\n")
                ofile.write("     XE_SM      1 1 1 1\n")
                ofile.write("     SEARCH     PPM\n")
                ofile.write("     XS_EXTRAP  1.0 0.3\n")
                ofile.write("     PIN_POWER  T\n")
                ofile.write("     PLOT_OPTS 0 0 0 0 0 2\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")
                
            with open(filename,"a") as ofile:             
                ofile.write("PARAM\n")
                ofile.write("     LSOLVER  1 1 20\n")
                ofile.write("     NODAL_KERN     NEMMG\n")
                ofile.write("     CMFD     2\n")
                ofile.write("     DECUSP   2\n")
                ofile.write("     INIT_GUESS 0\n")
                ofile.write("     CONV_SS   1.e-6 5.e-5 1.e-3 0.001\n")
                ofile.write("     EPS_ERF   0.010\n")
                ofile.write("     EPS_ANM   0.000001\n")
                ofile.write("     NLUPD_SS  5 5 1\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")
            

            with open(filename,"a") as ofile:             
                ofile.write("GEOM\n")
                ofile.write("     GEO_DIM 9 9 18 1 1\n")
                ofile.write("     RAD_CONF\n")
                for x in range(self.core_lattice.shape[0]):
                    ofile.write("     ")
                    for y in range(self.core_lattice.shape[1]):
                        ofile.write(self.core_lattice[x,y])
                        ofile.write("  ")
                    ofile.write("\n")
            
                ofile.write("     GRID_X      1*10.75 8*21.50\n")
                ofile.write("     NEUTMESH_X  1*1 8*1\n")
                ofile.write("     GRID_Y      1*10.75 8*21.50\n")
                ofile.write("     NEUTMESH_Y  1*1 8*1\n")
                ofile.write("     GRID_Z      30.48 15.24 10.16 5.08 10*30.48 5.08 10.16 15.24 30.48\n")            
                ofile.write("     ASSY_TYPE   10   1*2   16*2    1*2 REFL\n")
                for i in range(xs_unique.shape[0]):
                    if 'gd_0' in xs_unique[i]:
                        ofile.write("     ASSY_TYPE   {}   1*1 1*4  14*{}  1*4  1*3 FUEL\n".format(tag_unique[i],xs_ref[i]))
                    else:
                        ofile.write("     ASSY_TYPE   {}   1*1 1*4  1*4 12*{} 1*4 1*4  1*3 FUEL\n".format(tag_unique[i],xs_ref[i]))
                ofile.write("\n")

                ofile.write("     boun_cond   0 2 0 2 2 2\n")
                ofile.write("     SYMMETRY 4\n")

                ofile.write("     PINCAL_LOC\n")
                for x in range(pincal_loc.shape[0]):
                    ofile.write("      ")
                    for y in range(pincal_loc.shape[1]):
                        val = pincal_loc[x,y]
                        if np.isnan(val):
                            pass
                        else:
                            ofile.write(str(int(pincal_loc[x,y])))
                            ofile.write("  ")
                    ofile.write("\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")
            
            with open(filename,"a") as ofile:             
                ofile.write("FDBK\n")
                ofile.write("     FA_POWPIT     {} 21.5\n".format(np.round(self.power/193,4)))
                ofile.write("     GAMMA_FRAC    0.0208    0.0    0.0\n")
                ofile.write("     EFF_DOPLT   T  0.5556\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")


            with open(filename,"a") as ofile:   
                ofile.write("TH\n")          
                ofile.write("     FLU_TYP       0\n")
                ofile.write("     N_PINGT    264 25\n")
                ofile.write("     PIN_DIM      4.1 4.75 0.58 6.13\n")
                ofile.write("     FLOW_COND    {}  {}\n".format(np.round(self.inlet_temperature-273.15,2),np.round(self.flow/193,4)))
                ofile.write("     HGAP     11356.0\n")
                ofile.write("     N_RING   6\n")
                ofile.write("     THMESH_X       9*1\n")
                ofile.write("     THMESH_Y       9*1\n")
                ofile.write("     THMESH_Z       1 2 3 4 5 6 7 8 9 10 11 12\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")

            with open(filename,"a") as ofile:             
                ofile.write("DEPL\n")
                ofile.write("     TIME_STP  1 1 14*30\n")
                ofile.write("     INP_HST   './boc_exp.dep' -2 1\n")
                ofile.write("     PMAXS_F   1 '{}' 1\n".format(cdir + '/' + 'xs_gbot'))
                ofile.write("     PMAXS_F   2 '{}' 2\n".format(cdir + '/' + 'xs_grad'))
                ofile.write("     PMAXS_F   3 '{}' 3\n".format(cdir + '/' + 'xs_gtop'))
                ofile.write("     PMAXS_F   4 '{}' 4\n".format(cdir + '/' + 'xs_g250_gd_0_wt_0'))
                for i in range(xs_unique.shape[0]):
                    ofile.write("     PMAXS_F   {} '{}' {}\n".format(5+i,cdir + '/' + xs_unique[i],5+i))
                ofile.write("\n")
                ofile.write(".")

            # Run PARCS INPUT DECK
            
            parcscmd = "/cm/shared/codes/TRACE51341_PARCS_332/PARCS-v332_Exe/Executables/Linux/parcs-v332-linux2-intel-x64-release.x"
          
            print('Execute PARCS')
            print('Running in process')
            try:
                output = subprocess.check_output([parcscmd, filename], stderr=STDOUT, timeout=50)
                # Get Results
                if 'Finished' in str(output):
                    ofile = fname + '.out'
                    self.get_results(fname,pin_power=False)
                else:
                    self.parameters["cycle_length"]['value'] = np.random.uniform(0,10)
                    self.parameters["PinPowerPeaking"]['value'] = np.random.uniform(10,20)
                    self.parameters["FDeltaH"]['value'] = np.random.uniform(10,20)
                    self.parameters["max_boron"]['value'] = np.random.uniform(2000,5000)
                    self.additional_parameters= {}
                    self.additional_parameters["LCOE"] = 0.0
                    self.additional_parameters["Discharge_Burnup"]=0.0
                    self.additional_parameters["Assemblies_Costs"] = 0.0
        
                os.system('rm -f {}.parcs_pin*'.format(fname))

            except subprocess.TimeoutExpired:
                print('Timed out - killing')
            
                os.system('rm -f {}.parcs_pin*'.format(fname))
                self.parameters["cycle_length"]['value'] = np.random.uniform(0,10)
                self.parameters["PinPowerPeaking"]['value'] = np.random.uniform(10,20)
                self.parameters["FDeltaH"]['value'] = np.random.uniform(10,20)
                self.parameters["max_boron"]['value'] = np.random.uniform(2000,5000)
                self.additional_parameters= {}
                self.additional_parameters["LCOE"] = 0.0
                self.additional_parameters["Discharge_Burnup"]=0.0
                self.additional_parameters["Assemblies_Costs"] = 0.0

            print('{} calculation is done!'.format(self.name))
            os.chdir(pwd)
            gc.collect()  
            print('finished collecting garbage...')
            print('exiting evaluate...')


class Loading_PatternSimple_Solution(Solution):
    """
    Solution class for designing loading patterns using PARCS code.

    Parameters: None

    Written by Gregory Delipei. 01/08/2022
    """
    def __init__(self):
        Solution.__init__(self)
        self.type        = None
        self.number_pins = None
        self.model       = None
        self.symmetry    = None
        self.nrow=17
        self.ncol=17
        self.action_lower=-1
        self.action_upper=1
        self.core_dict={}
        
       
    def add_additional_information(self,settings):
        """
        Adds information on reactor parameters.

        Parameters
            settings: The settings dictionary for the parameters.
        
        Written by Gregory Delipei. 01/08/2022
        """
        self.symmetry=settings["genome"]["parcs_data"]["symmetry"]
        self.core_dict['core_map'], self.core_dict['core_id'] = self.generate_core()
        if 'inventory' in list(settings["genome"].keys()):
            self.core_dict['Inventory'] = settings["genome"]['inventory']
        else:
            inventory = {}
            for key,value in settings["genome"]["chromosomes"].items():
                inv_it = {}
                inv_it['Max_Limit']=np.inf
                inv_it['In_Design']=0
                inv_it['Cost']=250
                inv_it['Tag']=str(value['type'])
                inv_it['Cross_Section']=value['serial']
                inventory[key]=inv_it
            self.core_dict['Inventory'] = inventory
            inventory_groups = {}
            for key,value in self.core_dict['Inventory'].items():
                inventory_groups[key]={'Values': [key],
                                       'Limit': 'Max',
                                       'Limit_Value':np.inf}

            self.core_dict['Inventory_Groups'] = inventory_groups
       
        info = settings['genome']['parcs_data']
        if 'xs_library' in info:
            self.library = info['xs_library']
        if 'power' in info:
            self.power = float(info['power'])
        if 'flow' in info:
            self.flow = float(info['flow'])
        if 'inlet_temperature' in info:
            self.inlet_temperature = float(info['inlet_temperature'])
        if 'map_size' in info:
            self.map_size= info['map_size']
        if 'number_assemblies' in info:
            self.number_assemblies = int(info['number_assemblies'])

        if 'fixed_problem' == settings['optimization']['reproducer']:
            self.fixed_genome = True
        elif 'unique_genes' == settings['optimization']['reproducer']:
            self.fixed_genome = True

    def generate_core(self):
        """
        Generates the 17x17 core map with consistent identifiers and treatment of symmetry.

        Parameters: None
        Additional comments:
          - The core_map is manually defined as a list line by line starting from the top of the core.
          It is advised to use the following naming conention for reflector assemblies 'ABCDE' 
          with A being R, BC indicating the row number (00-17) and DE the column number (00-17). For 
          the fuel assemblies it is advised to use the following naming convention 'ABC' with A being the 
          row letter indetifier (A-O) and BC being the column number (00-17). 

        Written by Gregory Delipei 7/12/2022
        """
        core_map = [  None ,  None ,  None ,  None ,"R0004","R0005","R0006","R0007","R0008","R0009","R0010","R0011","R0012",  None ,  None ,  None ,  None ,
                      None ,  None ,"R0102","R0103","R0104", "A05" , "A06" , "A07" , "A08" , "A09" , "A10" , "A11" ,"R0112","R0113","R0114",  None ,  None ,
                      None ,"R0201","R0202", "B03" , "B04" , "B05" , "B06" , "B07" , "B08" , "B09" , "B10" , "B11" , "B12" , "B13" ,"R0214","R0215",  None ,
                      None ,"R0301", "C02" , "C03" , "C04" , "C05" , "C06" , "C07" , "C08" , "C09" , "C10" , "C11" , "C12" , "C13" , "C14" ,"R0315",  None ,
                    "R0400","R0401", "D02" , "D03" , "D04" , "D05" , "D06" , "D07" , "D08" , "D09" , "D10" , "D11" , "D12" , "D13" , "D14" ,"R0415","R0416",
                    "R0500", "E01" , "E02" , "E03" , "E04" , "E05" , "E06" , "E07" , "E08" , "E09" , "E10" , "E11" , "E12" , "E13" , "E14" , "E15" ,"R0516",
                    "R0600", "F01" , "F02" , "F03" , "F04" , "F05" , "F06" , "F07" , "F08" , "F09" , "F10" , "F11" , "F12" , "F13" , "F14" , "F15" ,"R0616",
                    "R0700", "G01" , "G02" , "G03" , "G04" , "G05" , "G06" , "G07" , "G08" , "G09" , "G10" , "G11" , "G12" , "G13" , "G14" , "G15" ,"R0716",
                    "R0800", "H01" , "H02" , "H03" , "H04" , "H05" , "H06" , "H07" , "H08" , "H09" , "H10" , "H11" , "H12" , "H13" , "H14" , "H15" ,"R0816",
                    "R0900", "I01" , "I02" , "I03" , "I04" , "I05" , "I06" , "I07" , "I08" , "I09" , "I10" , "I11" , "I12" , "I13" , "I14" , "I15" ,"R0916",
                    "R1000", "J01" , "J02" , "J03" , "J04" , "J05" , "J06" , "J07" , "J08" , "J09" , "J10" , "J11" , "J12" , "J13" , "J14" , "J15" ,"R1016",
                    "R1100", "K01" , "K02" , "K03" , "K04" , "K05" , "K06" , "K07" , "K08" , "K09" , "K10" , "K11" , "K12" , "K13" , "K14" , "K15" ,"R1116",
                    "R1200","R1201", "L02" , "L03" , "L04" , "L05" , "L06" , "L07" , "L08" , "L09" , "L10" , "L11" , "L12" , "L13" , "L14" ,"R1215","R1216",
                      None ,"R1301", "M02" , "M03" , "M04" , "M05" , "M06" , "M07" , "M08" , "M09" , "M10" , "M11" , "M12" , "M13" , "M14" ,"R1315",  None ,
                      None ,"R1401","R1402", "N03" , "N04" , "N05" , "N06" , "N07" , "N08" , "N09" , "N10" , "N11" , "N12" , "N13" ,"R1414","R1415",  None ,
                      None ,  None ,"R1502","R1503","R1504", "O05" , "O06" , "O07" , "O08" , "O09" , "O10" , "O11" ,"R1512","R1513","R1514",  None ,  None ,
                      None ,  None ,  None ,  None ,"R1604","R1605","R1606","R1607","R1608","R1609","R1610","R1611","R1612",  None ,  None ,  None ,  None ]
        core_map = np.array(core_map).reshape((self.nrow,self.ncol))
        core_id = []
        for i in range(self.nrow-1,-1,-1):
            for j in range(self.ncol):
                core_id.append((i-8,j-8))
        core_id=np.array(core_id).reshape((self.nrow,self.ncol,2))
        if self.symmetry == 'quarter':
            self.core_dict['core'], self.core_dict['fuel'] = self.quarter_core(core_map,core_id)
        elif self.symmetry == 'octant':
            self.symmetry_axes = ((8,8),(16,16),(16,8))
            self.core_dict['core'], self.core_dict['fuel'] = self.octant_core(core_map,core_id)
        else:
            raise ValueError(
                f"The selected symmetry ({self.symmetry}) is not valid."
            )
        return(core_map, core_id)

    def get_full_core(self):
        """
        Generates the 17x17 full fuel core from symmetry.

        Parameters: None
    
        Written by Gregory Delipei 7/24/2022
        """
        full_core  = {}
        for key, value in self.core_dict['fuel'].items():
            full_core[key]=value['Value']
            for skey in value['Symmetric_Assemblies']:
               full_core[skey]=value['Value'] 
        return(full_core)

    def quarter_core(self,core_map,core_id):
        """
        Generates the quarter core symmetry map.

        Parameters: 
           - core_map: a 17x17 numpy array with the fuel assembly location names.
           - core_id: a 17x17x2 numpy array with coordinate indices for each fuel assembly location
           ranging from -8 to +8.

        Written by Gregory Delipei 7/12/2022
        """
        sym_center = self.symmetry_axes[0]
        sym_horizontal = self.symmetry_axes[1]
        sym_vertical = self.symmetry_axes[2]
        if sym_vertical[0] > sym_center[0]:
            row_iter = np.arange(sym_center[0],sym_vertical[0]+1,1)
        else:
            row_iter = np.arange(sym_center[0],sym_vertical[0]-1,-1)
        if sym_horizontal[1] > sym_center[1]:
            col_iter = np.arange(sym_center[1],sym_horizontal[1]+1,1)
        else:
            col_iter = np.arange(sym_center[1],sym_horizontal[1]-1,-1)

        core_dict={}
        for irow in row_iter:
            for icol in col_iter:
                dict_value={'Symmetric_Assemblies':[],
                            'Value': None}
                if (irow,icol) == sym_center:
                    pass
                elif irow == sym_horizontal[0] and icol != sym_center[1]:                 
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == idy) & (core_id[:,:,1] == -idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0]]
                elif icol == sym_vertical[1] and irow != sym_center[0]:
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0]]
                else:
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    idxy_2= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == -idx))
                    idxy_3= np.where((core_id[:,:,0] == idy) & (core_id[:,:,1] == -idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0], core_map[idxy_2][0], core_map[idxy_3][0]]
                core_dict[core_map[irow,icol]] = dict_value
                fuel_dict = self.extract_fuel(core_dict)
        return(core_dict,fuel_dict)
        
    def octant_core(self, core_map, core_id):
        """
        Generates the octant core symmetry map.

        Parameters: 
           - core_map: a 17x17 numpy array with the fuel assembly location names.
           - core_id: a 17x17x2 numpy array with coordinate indices for each fuel assembly location
           ranging from -8 to +8.

        Written by Gregory Delipei 7/12/2022
        """
        sym_center = self.symmetry_axes[0]
        sym_corner = self.symmetry_axes[1]
        sym_vertical = self.symmetry_axes[2]
        if sym_corner[0] > sym_center[0]:
            row_iter = np.arange(sym_center[0],sym_corner[0]+1,1)
        else:
            row_iter = np.arange(sym_center[0],sym_corner[0]-1,-1)
        if sym_corner[1] > sym_center[1]:
            col_iter = np.arange(sym_center[1],sym_corner[1]+1,1)
        else:
            col_iter = np.arange(sym_center[1],sym_corner[1]-1,-1)

        core_dict={}
        for irow in row_iter:
            for icol in col_iter:
                if icol>irow:
                    continue
                dict_value={'Symmetric_Assemblies':[],
                            'Value': None}
                if (irow,icol) == sym_center:
                    pass
                elif icol == sym_vertical[1] and irow != sym_center[0]:                 
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == idx) & (core_id[:,:,1] == -idy))
                    idxy_2= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    idxy_3= np.where((core_id[:,:,0] == idx) & (core_id[:,:,1] == idy))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0], core_map[idxy_2][0], core_map[idxy_3][0]]
                elif icol == irow and irow != sym_center[0]:
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    idxy_2= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == -idx))
                    idxy_3= np.where((core_id[:,:,0] == idy) & (core_id[:,:,1] == -idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0], core_map[idxy_2][0], core_map[idxy_3][0]]
                else:
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == -idx) & (core_id[:,:,1] == -idy))
                    idxy_2= np.where((core_id[:,:,0] == idx) & (core_id[:,:,1] == -idy))
                    idxy_3= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    idxy_4= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == -idx))
                    idxy_5= np.where((core_id[:,:,0] == idx) & (core_id[:,:,1] == idy))
                    idxy_6= np.where((core_id[:,:,0] == -idx) & (core_id[:,:,1] == idy))
                    idxy_7= np.where((core_id[:,:,0] == idy) & (core_id[:,:,1] == -idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0], core_map[idxy_2][0], core_map[idxy_3][0], core_map[idxy_4][0],
                                                          core_map[idxy_5][0], core_map[idxy_6][0], core_map[idxy_7][0]]
                core_dict[core_map[irow,icol]] = dict_value
                fuel_dict = self.extract_fuel(core_dict)
        return(core_dict,fuel_dict)

    def extract_fuel(self, core_dict):
        """
        Extracts the unique fuel assemblies from the core in a dictionary.

        Parameters: 
           - core_dict: a core dictionary including all the geometrical parameters.

        Written by Gregory Delipei 7/12/2022
        """
        fuel_dict={}
        for key, value in core_dict.items():
            if key is None:
                continue
            elif key[0]=="R":
                continue
            else:
                fuel_dict[key]=value
        return(fuel_dict)

    def random_design(self):
        """
        Generates a random design following the constraints in the inventory.

        Parameters: None

        Written by Gregory Delipei 7/13/2022
        """

        # Initialization

        avail_locations=list(self.core_dict['fuel'].keys())
        assembly_types = list(self.core_dict['Inventory'].keys())

        for iass in assembly_types:
            self.core_dict['Inventory'][iass]['In_Desing'] = 0

        assembly_types_group = copy.deepcopy(assembly_types)
        avail_locations_group = copy.deepcopy(avail_locations)
        maxiter=10000 # maximum iterations to avoid infinite loop.
        nfuel, nfuel_sym, nrefl, nrefl_sym = self.compute_fa_number()
        total_fuel = nfuel
        total=0

        # Select randomly the fuel assemblies with exact limits in the inventory groups
        for key, value in self.core_dict['Inventory_Groups'].items():
            total_group=0
            if value['Limit']=='Exact':
                niter=0
                while total_group != value['Limit_Value'] and niter<maxiter:
                    avail_choices = []
                    for iloc in avail_locations_group:
                        for iass in value['Values']:
                            proposed_choice = (iloc, iass)
                            symmetry_multiplier = len(self.core_dict['fuel'][iloc]['Symmetric_Assemblies'])+1
                            if (total_group + symmetry_multiplier <= value['Limit_Value']) and (self.core_dict['Inventory'][iass]['In_Design'] <= self.core_dict['Inventory'][iass]['Max_Limit']-symmetry_multiplier):
                                avail_choices.append(proposed_choice)
                    # Re-iterate if the selected random filling strategy cannot meet the inventory limits.
                    if len(avail_choices)==0:
                        total_group=0
                        niter +=1
                        avail_locations_group = copy.deepcopy(avail_locations)
                        for iass in assembly_types_group:
                            self.core_dict['Inventory'][iass]['In_Design'] = 0
                        print(f"New Exact Filling Strategy - {niter}")
                        continue

                    sampled_choice = random.choice(avail_choices)
                    sloc = sampled_choice[0]
                    sass = sampled_choice[1]
                    self.core_dict['fuel'][sloc]['Value']=sass
                    self.core_dict['core'][sloc]['Value']=sass
                    symmetry_multiplier = len(self.core_dict['fuel'][sloc]['Symmetric_Assemblies'])+1
                    self.core_dict['Inventory'][sass]['In_Design']+= symmetry_multiplier
                    avail_locations_group.remove(sloc)
                    total_group+=symmetry_multiplier

                # Update the remaining available quantities for the next inventory groups
                for iass in value['Values']:
                    assembly_types_group.remove(iass)
                avail_locations = copy.deepcopy(avail_locations_group)
                assembly_types=copy.deepcopy(assembly_types_group)
                total+=total_group
        
        # Select randomly the fuel assemblies without exact limits in the inventory groups
        niter=0
        while total != total_fuel and niter<maxiter:
            avail_choices = []
            for iloc in avail_locations:
                for key, value in self.core_dict['Inventory_Groups'].items(): 
                    if value['Limit']!='Exact':
                        subtotal = 0
                        for iass in value["Values"]:
                            subtotal+=self.core_dict['Inventory'][iass]['In_Design']
                        for iass in value["Values"]:
                            proposed_choice = (iloc, iass)
                            symmetry_multiplier = len(self.core_dict['fuel'][iloc]['Symmetric_Assemblies'])+1
                            if (self.core_dict['Inventory'][iass]['In_Design'] <= self.core_dict['Inventory'][iass]['Max_Limit']-symmetry_multiplier) and (subtotal <=value['Limit_Value']-symmetry_multiplier):
                                avail_choices.append(proposed_choice)
      
            # Re-iterate if the selected random filling strategy cannot meet the inventory limits.
            if len(avail_choices)==0:
                total=total_group
                niter +=1
                avail_locations = copy.deepcopy(avail_locations_group)
                for iass in assembly_types:
                    self.core_dict['Inventory'][iass]['In_Desing'] = 0
                print(f"New Filling Strategy - {niter}")
                continue
            sampled_choice = random.choice(avail_choices)
            sloc = sampled_choice[0]
            sass = sampled_choice[1]
            self.core_dict['fuel'][sloc]['Value']=sass
            self.core_dict['core'][sloc]['Value']=sass
            symmetry_multiplier = len(self.core_dict['fuel'][sloc]['Symmetric_Assemblies'])+1
            self.core_dict['Inventory'][sass]['In_Design']+= symmetry_multiplier
            avail_locations.remove(sloc)
            total+=symmetry_multiplier

        return
    
    def action(self,act):
        """
        Performs an action on the current design and updates it.

        Parameters: 
            - act: Dictionary with the action options.

        Written by Gregory Delipei 7/14/2022
        """
        avail_actions = self.get_actions()
        action_type = act['Type']
        action_location = act['Location']
        action = act['Value']

        if action in avail_actions[action_type][action_location]:
            if action_type =='Exchange':
                loc_value = self.core_dict['core'][action_location]['Value']
                action_value = self.core_dict['core'][action]['Value']
                self.core_dict['core'][action_location]['Value'] = action_value
                self.core_dict['fuel'][action_location]['Value'] = action_value
                self.core_dict['core'][action]['Value'] = loc_value
                self.core_dict['fuel'][action]['Value'] = loc_value
            elif action_type=='Change':
                loc_value = self.core_dict['core'][action_location]['Value']
                loc_symmetry=len(self.core_dict['fuel'][action_location]['Symmetric_Assemblies'])+1
                self.core_dict['core'][action_location]['Value'] = action
                self.core_dict['fuel'][action_location]['Value'] = action
                self.core_dict['Inventory'][loc_value]['In_Design']-=loc_symmetry
                self.core_dict['Inventory'][action]['In_Design']+=loc_symmetry
        else:
            raise ValueError(
                f"The selected action is not valid."
            )
        return

    def mapaction(self,mact):
        """
        Performs an action on the current design and updates it.

        Parameters: 
            - act: Dictionary with the action options.

        Written by Gregory Delipei 7/14/2022
        """
        avail_actions = self.get_actions()
        action_mvalue = mact['Value']
        action_location = mact['Location']
        loc_actions=avail_actions['Map'][action_location]
        action_space = mact['Space']
        cmap = mact['Action_Map']
        for key,value in loc_actions.items():
            if action_space=="continuous":
                bounds = value['Bounds']
                if bounds[0]<=action_mvalue<bounds[1]:
                    action_type = value['Type']
                    action = value['Value']
                if action_mvalue==bounds[1]==1:
                    action_type = value['Type']
                    action = value['Value']
            elif action_space == "discrete":
                if cmap[value['Value']]==action_mvalue:
                    action_type = value['Type']
                    action = value['Value']
                    
        if action in avail_actions[action_type][action_location]:
            if action_type =='Exchange':
                loc_value = self.core_dict['core'][action_location]['Value']
                action_value = self.core_dict['core'][action]['Value']
                self.core_dict['core'][action_location]['Value'] = action_value
                self.core_dict['fuel'][action_location]['Value'] = action_value
                self.core_dict['core'][action]['Value'] = loc_value
                self.core_dict['fuel'][action]['Value'] = loc_value
            elif action_type=='Change':
                loc_value = self.core_dict['core'][action_location]['Value']
                loc_symmetry=len(self.core_dict['fuel'][action_location]['Symmetric_Assemblies'])+1
                self.core_dict['core'][action_location]['Value'] = action
                self.core_dict['fuel'][action_location]['Value'] = action
                self.core_dict['Inventory'][loc_value]['In_Design']-=loc_symmetry
                self.core_dict['Inventory'][action]['In_Design']+=loc_symmetry
            new_state = {}
            for key, value in self.core_dict['fuel'].items():
                new_state[key]=value['Value']
            self.set_state(new_state)
        else:
            raise ValueError(
                f"The selected action is not valid."
            )
        return

    def get_actions(self):
        """
        Extracts all possible actions in a dictionary.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """

        # Compute exchange type of actions
        # exchange_act = {}
        # for key, value in self.core_dict["fuel"].items():
        #     avail_choices=[]
        #     key_symmetry = len(self.core_dict['fuel'][key]['Symmetric_Assemblies'])+1
        #     for key_ex,value_ex in  self.core_dict["fuel"].items():
        #         key_ex_symmetry = len(self.core_dict['fuel'][key_ex]['Symmetric_Assemblies'])+1
        #         if key_symmetry == key_ex_symmetry:
        #             selected_choice=key_ex
        #             avail_choices.append(selected_choice)
        #     exchange_act[key]=avail_choices

        # Compute change type of actions
        change_act = {}
        
        for key, value in self.core_dict["fuel"].items():
            avail_choices=[]
            loc_symmetry = len(self.core_dict['fuel'][key]['Symmetric_Assemblies'])+1
            loc_value = self.core_dict['fuel'][key]['Value']
            loc_group = self.get_inventory_group(loc_value)
            loc_group_limit = self.core_dict['Inventory_Groups'][loc_group]['Limit']
            for key_group,value_group in  self.core_dict['Inventory_Groups'].items(): 
                key_group_limit = self.core_dict['Inventory_Groups'][key_group]['Limit']
                for iass in value_group["Values"]:
                    if loc_group_limit=='Exact' and key_group==loc_group:
                        iass_limit = self.core_dict['Inventory'][iass]['Max_Limit']
                        iass_indesign = self.core_dict['Inventory'][iass]['In_Design']
                        if loc_symmetry + iass_indesign <= iass_limit:
                            selected_choice = iass
                            avail_choices.append(selected_choice)
                    elif loc_group_limit=='Max' and key_group_limit=='Max' and key_group!=loc_group:
                        iass_limit = self.core_dict['Inventory'][iass]['Max_Limit']
                        iass_indesign = self.core_dict['Inventory'][iass]['In_Design']
                        group_limit = value_group['Limit_Value']
                        group_indesign = self.get_group_indesign(key_group)
                        if (loc_symmetry + iass_indesign <= iass_limit) and (loc_symmetry + group_indesign <= group_limit):
                            selected_choice = iass
                            avail_choices.append(selected_choice)
                    elif loc_group_limit=='Max' and key_group_limit=='Max' and key_group==loc_group:
                        iass_limit = self.core_dict['Inventory'][iass]['Max_Limit']
                        iass_indesign = self.core_dict['Inventory'][iass]['In_Design']
                        if (loc_symmetry + iass_indesign <= iass_limit):
                            selected_choice = iass
                            avail_choices.append(selected_choice)
            change_act[key]=avail_choices

        # Create mapping from [0,1] to action
        map_act = {}
        for key, value in self.core_dict["fuel"].items():
        #    nex_act = len(exchange_act[key])
            nex_act=0
            nch_act = len(change_act[key])
            nact = nex_act + nch_act
            act_bounds = np.linspace(self.action_lower,self.action_upper,nact+1)
            mdict={}
            it=0
            for i in range(nch_act):
                it+=1
                adict={}
                adict['Bounds'] = np.array([act_bounds[it-1],act_bounds[it]])
                adict['Type'] = 'Change'
                adict['Value'] = change_act[key][i]
                mdict['Act'+str(it)] = adict
            # for i in range(nex_act):
            #     it+=1
            #     adict={}
            #     adict['Bounds'] = np.array([act_bounds[it-1],act_bounds[it]])
            #     adict['Type'] = 'Exchange'
            #     adict['Value'] = exchange_act[key][i]
            #     mdict['Act'+str(it)] = adict
            map_act[key]=mdict
                
        # act_dict={'Exchange': exchange_act,
        #           'Change': change_act,
        #           'Map': map_act}
        act_dict={'Change': change_act,
                  'Map': map_act}
        return(act_dict)

    def get_mapstate(self,cmap,observation_type):
        """
        Gets the current state in a normalized format.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """
        if observation_type=='continuous':
            mstate=np.zeros(len(self.core_dict['fuel'].keys()),dtype=np.int8)
        elif observation_type=='multi_discrete':
            mstate=np.zeros(len(self.core_dict['fuel'].keys())+1,dtype=np.int8)
        it=0
        for key, value in self.core_dict['fuel'].items():
            mstate[it]=cmap[value['Value']]
            it+=1
        return(mstate)

    def get_inventory_group(self,iass):
        """
        Get in which group an assembly belongs to.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """
        igroup = None
        for key,value in self.core_dict['Inventory_Groups'].items():
            if iass in value['Values']:
                igroup = key
        return(igroup)
    
    def get_group_indesign(self,group):
        """
        Get in which group an assembly belongs to.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """
        sum_in = 0
        for iass in self.core_dict['Inventory_Groups'][group]['Values']:
            sum_in += self.core_dict['Inventory'][iass]['In_Design']
        return(sum_in)

    def plot_design(self,filepath):
        """
        Plot current loading pattern design.

        Parameters: None

        Written by Gregory Delipei 7/13/2022
        """
        color_fill = ['maroon','red','darkorange','limegreen','turquoise','pink','purple','plum','teal']
        nfa = 1
        tags=[]
        for key in self.core_dict['Inventory'].keys():
            if self.core_dict['Inventory'][key]['In_Design'] > 0:
                nfa+=1
                tags.append(key)
        ass_pitch = 21.21      

        plt.rcParams.update({'font.size': 4})
        fig=plt.figure()
        plt.axes()

        value_map = copy.deepcopy(self.core_dict['core_map'])
        value_map = value_map.astype('<U12')
        for key, value in self.core_dict['core'].items():
            value_map[np.where(self.core_dict['core_map']==key)] = value['Value']
            for isym in value['Symmetric_Assemblies']:
                value_map[np.where(self.core_dict['core_map']==isym)] = value['Value']

        for i in range(17):
            for j in range(17):
                ass_type=value_map[i,j]
                yloc=self.core_dict['core_id'][i,j][0]
                xloc=self.core_dict['core_id'][i,j][1]
                yid = yloc*ass_pitch
                xid = xloc*ass_pitch
                if ass_type == 'None':
                    continue
                else:
                    ass_color = color_fill[tags.index(ass_type)]
                    rectangle = plt.Rectangle((xid,yid),ass_pitch, ass_pitch,fc=ass_color,ec='grey')
                    plt.gca().add_patch(rectangle)
                    plt.text(xid+5,yid+9,self.core_dict['core_map'][i,j])


        plt.rcParams.update({'font.size': 8})
        rectangle = plt.Rectangle((12*ass_pitch,8*ass_pitch),0.3*ass_pitch,0.2*ass_pitch,1,fc="White")
        plt.gca().add_patch(rectangle)
        for i in range(len(tags)):    
            rectangle = plt.Rectangle((9.0*ass_pitch,8*ass_pitch-i*ass_pitch),0.4*ass_pitch,0.3*ass_pitch,1,fc=color_fill[i])
            plt.gca().add_patch(rectangle)
            plt.text(9.5*ass_pitch,8*ass_pitch-i*ass_pitch-0.03*ass_pitch,tags[i])

        plt.axis('scaled')
        plt.tick_params(left = False, right = False , labelleft = False ,
                        labelbottom = False, bottom = False)

        plt.savefig(filepath,bbox_inches='tight',dpi=300) 
        plt.close(fig)

    def compute_fa_number(self):
        """
        Computes the total number of fuel/reflector assemblies in the core with and without symmetry.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """
        nfuel=0
        nfuel_sym=0
        nrefl = 0
        nrefl_sym = 0
        for key, value in self.core_dict['core'].items():
            symmetry_multiplier = len(self.core_dict['core'][key]['Symmetric_Assemblies'])+1
            if key is None:
                continue
            elif key[0]=='R':
                nrefl_sym+=1
                nrefl+=symmetry_multiplier
            else:
                nfuel_sym+=1
                nfuel+=symmetry_multiplier
        return(nfuel,nfuel_sym,nrefl,nrefl_sym)

        return
    
    def set_state(self,state):
        
        for key,value in self.core_dict['Inventory'].items():
            nvalue = value['In_Design']=0
            self.core_dict['Inventory'][key] = value
        
        self.genome=[]
        for key, value in state.items():
            symmetry_multiplier = len(self.core_dict['fuel'][key]['Symmetric_Assemblies'])+1
            self.core_dict['fuel'][key]['Value']=value
            self.genome.append(value)
            self.core_dict['core'][key]['Value']=value
            self.core_dict['Inventory'][value]['In_Design']+=symmetry_multiplier
        return

    def get_state(self):
        state={}
        for key, value in self.core_dict['fuel'].items():
            state[key]=value['Value']
        return(state)
    
    def genes_in_group(self,chromosome_map,group_name):
        """
        Returns a list of the genes in the chosen group
        """
        gene_list = []
        for gene in chromosome_map:
            if gene == 'symmetry_list':
                pass
            else:
                if group_name == chromosome_map[gene]['gene_group']:
                    gene_list.append(gene)

        return gene_list

    def is_gene_ok(self,chromosome_map,gene,space):
        """
        Checks if the gene is allowed in the desired location
        """
        gene_is_ok = True
        if not chromosome_map[gene]['map'][space]:
            gene_is_ok = False
        if space in chromosome_map['symmetry_list']:
            if self.my_group[chromosome_map[gene]['gene_group']] <= 1:
                gene_is_ok = False
        else:
            if not self.my_group[chromosome_map[gene]['gene_group']]:
                gene_is_ok = False
        if 'unique' in chromosome_map[gene]:
            if gene in self.genome:
                gene_is_ok = False

        return gene_is_ok

    def generate_initial(self,chromosome_map):
        """
        Generates the initial solutions to the optimization problem.

        Parameters: 
            chromosome_map: Dictionary
                The genome portion of the dictionary settings file. 

        Written by Brian Andersen. 1/9/2020
        """
        chromosome_length = None
        chromosome_list = list(chromosome_map.keys())
        if 'symmetry_list' in chromosome_list:
            chromosome_list.remove('symmetry_list')

        for chromosome in chromosome_list:
            if chromosome_length is None:
                chromosome_length = len(chromosome_map[chromosome]['map'])
            elif len(chromosome_map[chromosome]['map']) == chromosome_length:
                pass
            else:
                raise ValueError("Chromosome Maps are of unequal length")

        self.genome = []                                #Unburnt assemblies
        for i in range(chromosome_length):              #better off just being implemented
            no_gene_found = True                        #as a single gene.
            while no_gene_found:
                gene = random.choice(chromosome_list)
                if chromosome_map[gene]['map'][i]:
                    self.genome.append(gene)
                    no_gene_found = False
        
    def generate_initial_fixed(self,chromosome_map,gene_groups):
        """
        Generates initial solution when only specific number of assemblies
        may be used.

        Written by Brian Andersen 3/15/2020
        """
        chromosome_length = None
        chromosome_list = list(chromosome_map.keys())
        if 'symmetry_list' in chromosome_list:
            chromosome_list.remove('symmetry_list')

        for chromosome in chromosome_list:
            if chromosome_length is None:
                chromosome_length = len(chromosome_map[chromosome]['map'])
            elif len(chromosome_map[chromosome]['map']) == chromosome_length:
                pass
            else:
                raise ValueError("Chromosome Maps are of unequal length")

        no_valid_solution = True
        while no_valid_solution:
            no_valid_solution = False
            my_group = copy.deepcopy(gene_groups)
            self.genome = [None]*chromosome_length
            for i in range(chromosome_length):
                no_gene_found = True
                attempt_counter = 0
                while no_gene_found:
                    gene = random.choice(chromosome_list)
                    if 'unique' in chromosome_map[gene]:
                        if chromosome_map[gene]['unique']:
                            if gene in self.genome:
                                pass
                            else:
                                #This else loop activates if the gene is labeled unique but is not used. 
                                if chromosome_map[gene]['map'][i] == 1:
                                    if i in chromosome_map['symmetry_list']:
                                        if my_group[chromosome_map[gene]['gene_group']] > 1:
                                            self.genome[i] = gene
                                            no_gene_found = False
                                            my_group[chromosome_map[gene]['gene_group']] -= 2
                                    else:
                                        if my_group[chromosome_map[gene]['gene_group']] > 0:
                                            self.genome[i] = gene
                                            no_gene_found = False
                                            my_group[chromosome_map[gene]['gene_group']] -= 1            
                        else:
                            #adding unique loop above this code
                            if chromosome_map[gene]['map'][i] == 1:
                                if i in chromosome_map['symmetry_list']:
                                    if my_group[chromosome_map[gene]['gene_group']] > 1:
                                        self.genome[i] = gene
                                        no_gene_found = False
                                        my_group[chromosome_map[gene]['gene_group']] -= 2
                                else:
                                    if my_group[chromosome_map[gene]['gene_group']] > 0:
                                        self.genome[i] = gene
                                        no_gene_found = False
                                        my_group[chromosome_map[gene]['gene_group']] -= 1
                    else:
                        #adding unique loop above this code
                        if chromosome_map[gene]['map'][i] == 1:
                            if i in chromosome_map['symmetry_list']:
                                if my_group[chromosome_map[gene]['gene_group']] > 1:
                                    self.genome[i] = gene
                                    no_gene_found = False
                                    my_group[chromosome_map[gene]['gene_group']] -= 2
                            else:
                                if my_group[chromosome_map[gene]['gene_group']] > 0:
                                    self.genome[i] = gene
                                    no_gene_found = False
                                    my_group[chromosome_map[gene]['gene_group']] -= 1
                    attempt_counter += 1
                    if attempt_counter == 100:
                        no_gene_found = False
                        no_valid_solution = True

    def new_generate_initial_fixed(self,chromosome_map,gene_groups):
        """
        Generates initial solution when only speciific number of assemblies may be used.

        Written by Brian Andersen 3/15/2020. Last edited 11/20/2020
        """
        #above here is the old code
        chromosome_length = None
        chromosome_list = list(chromosome_map.keys())
        if 'symmetry_list' in chromosome_list:
            chromosome_list.remove('symmetry_list')

        for chromosome in chromosome_list:
            if chromosome_length is None:
                chromosome_length = len(chromosome_map[chromosome]['map'])
            elif len(chromosome_map[chromosome]['map']) == chromosome_length:
                pass
            else:
                raise ValueError("Chromosome Maps are of unequal length")

        no_genome_found = True
        while no_genome_found:
            attempts = 0
            self.my_group = copy.deepcopy(gene_groups)
            self.genome = [None]*chromosome_length
            unfilled_spaces = list(range(chromosome_length))
            while unfilled_spaces:  
                space_number = random.randint(0,len(unfilled_spaces)-1)
                group_name = None
                while not group_name:
                    random_group = random.choice(list(self.my_group.keys()))
                    if self.my_group[random_group] > 0:
                        group_name = random_group
                available_gene_list = self.genes_in_group(chromosome_map,group_name)
                space = unfilled_spaces[space_number]
                gene = random.choice(available_gene_list)
                gene_is_ok = self.is_gene_ok(chromosome_map,gene,space)
                if gene_is_ok:
                    self.genome[space] = gene
                    unfilled_spaces.remove(space)
                    if space in chromosome_map['symmetry_list']:
                        self.my_group[chromosome_map[gene]['gene_group']] -= 2
                    else:
                        self.my_group[chromosome_map[gene]['gene_group']] -= 1             
                else:
                    attempts += 1
                if attempts == 100:
                    break

            bad_gene_list = []
            for i,gene in enumerate(self.genome):
                if not gene:
                    bad_gene_list.append(i)

            if not bad_gene_list:
                no_genome_found = False                

    def get_clength(self,efpd,boron,keff):
        if boron[-1]==0.1:
            eoc1_ind = 0
            eco2_ind = len(efpd)
            for i in range(len(efpd)):
                if boron[i] > 0.1 and boron[i+1] == 0.1:
                    eoc1_ind = i
                    eco2_ind = i+1
            dbor = abs(boron[eoc1_ind-1]-boron[eoc1_ind])
            defpd = abs(efpd[eoc1_ind-1]-efpd[eoc1_ind])
            def_dbor = defpd/dbor
            eoc = efpd[eoc1_ind] + def_dbor*(boron[eoc1_ind]-0.1)
        elif boron[-1]==boron[0]==1800.0:
            drho_dcb=10 
            drho1 = (keff[-2]-1.0)*10**5
            dcb1 = drho1/drho_dcb
            cb1= boron[-2] + dcb1
            drho2 = (keff[-1]-1.0)*10**5
            dcb2 = drho2/drho_dcb
            cb2= boron[-1] + dcb2
            dbor = abs(cb1-cb2)
            defpd = abs(efpd[-2]-efpd[-1])
            def_dbor = defpd/dbor
            eoc = efpd[-1] + def_dbor*(cb2-0.1)
        else:
            dbor = abs(boron[-2]-boron[-1])
            defpd = abs(efpd[-2]-efpd[-1])
            def_dbor = defpd/dbor
            eoc = efpd[-1] + def_dbor*(boron[-1]-0.1)
        return(eoc)

    def get_pin_power(self,filepath):
        start = time.time()
        print('Reading of Pin Powers')
        npx=17
        npy=17
        npin = npx*npy
        nbu = 17
        nz=12
        nasb = self.compute_nasb()
        pp_mat = np.zeros((nbu,nasb,nz,npin))
        for iasb in range(nasb):
            pinfile = filepath + ".parcs_pin" + str(iasb+1).zfill(3)
            ofile = open(pinfile, "r")
            filestr = ofile.read()
            ofile.close()
            asbstr = filestr.split('  Case:')
            for i in range(1,len(asbstr)):
                asb_line =asbstr[i].split('\n')
                ibu=int(asb_line[0][0:4])-1
                iz_val = int(asb_line[0][66:68])
                if iz_val == 0:
                    continue
                else:
                    iz = iz_val-2
                    pp_str = asb_line[2:2+npy]
                    for iy in range(npy):
                        for ix in range(npx):
                            pp_id = iy*npx + ix 
                            try:
                                pp_mat[ibu,iasb,iz,pp_id] = float(pp_str[iy][(7*ix + 8):(7*ix + 14)])
                            except:
                                print("Non physical peaking factors")
                                pp_mat[ibu,iasb,iz,pp_id] = 10.0

        end = time.time()
        print('Pin Power Duration = {} s'.format(end-start))
        return(pp_mat)

    def get_asb_power(self,filepath):
        start = time.time()
        print('Reading of Assembly Powers')
        ofile = open(filepath+".parcs_dep", "r")
        filestr = ofile.read()
        ofile.close()
        bustr=filestr.split(" RPF 3D MAP")
        nbu= len(bustr)-1
        nz_str = bustr[0].split(' RPF 1D MAP')[1].split('\n')
        nrefl=2
        nz = len(nz_str)-4-nrefl
        ztag = np.arange(2,nz+1 + 1)
        nasb = self.compute_nasb()
        asb_mat = np.zeros((nbu,nasb,nz))
        for ibu in range(nbu):
            ibustr = bustr[ibu+1].split(' EXP 2D MAP')[0]
            asb_str = ibustr.split(' k lb')
            iasb=0
            for ik in range(1,len(asb_str)):
                asb_line=asb_str[ik].split('\n')
                for iz in range(1,len(asb_line)):
                    asb_val=asb_line[iz].split()
                    if len(asb_val)>0:
                        if int(asb_val[0]) in ztag:
                            zid = int(asb_val[0])-2
                            asb_count = 0
                            for ia in range(1,len(asb_val)):
                                val = float(asb_val[ia])
                                if  val !=0.0:
                                    asb_id = iasb + asb_count
                                    asb_mat[ibu,asb_id,zid]=val
                                    asb_count+=1
                                else:
                                    continue
                    else:
                        continue
                iasb += asb_count
        end = time.time()
        print('Assembly Power Duration = {} s'.format(end-start))
        return(asb_mat)

    def get_lcoe(self):
        
        cycle_param={'EFPD': self.parameters['cycle_length']['value'],
                    'Batches': 3,
                    'Thermal_Power': self.power,
                    'Efficiency': 0.33,
                    'Fuel_Assemblies': self.number_assemblies}

        lcoe_param={'Discount_Rate': 0.07,
                    'Uranium_Ore_Price': 80,
                    'Conversion_Price': 10,
                    'Enrichment_Price': 160,
                    'Fabrication_Price': 250,
                    'Uranium_Ore_Loss': 0.002,
                    'Conversion_Loss': 0.002,
                    'Enrichment_Loss': 0.002,
                    'Fabrication_Loss': 0.002,
                    'Enrichment_Feed': 0.00711,
                    'Enrichment_Tail': 0.003,
                    'Storage_Price': 200,
                    'Disposal_Price': 463,
                    'Uranium_Ore_Time': -2.0,
                    'Conversion_Time': -1.5,
                    'Enrichment_Time': -1.0,
                    'Fabrication_Time': -0.5,
                    'Storage_Time': 5.0+cycle_param['EFPD']*cycle_param['Batches']/365.25,
                    'Disposal_Time': cycle_param['EFPD']*cycle_param['Batches']/365.25}

        unique_fa =  np.unique(list(self.full_core.values()))
        asb_param = {}
        for i in range(len(unique_fa)):
            nfa = list(self.full_core.values()).count(unique_fa[i])
            enr = float(unique_fa[i][2:5])/10000
            asb_dict = {'Number': nfa,
                        'Fuel_Rods': 264,
                        'Fuel_Radius': 0.41,
                        'Fuel_Height': 365.76,
                        'Enrichment': enr,
                        'Fuel_Density': 10.23,
                        'Fabrication_Price': 250
                        }
            asb_param[unique_fa[i]]=asb_dict

        lcoe, bu, asb_cost = LCOE(cycle_param,lcoe_param, asb_param)
        asb_cost_dict = {}
        for i in range(len(unique_fa)):
            asb_cost_dict[unique_fa[i]]=asb_cost[i]

        return((lcoe, bu, asb_cost_dict))

    def get_fitness(self):
        
        fit = 0 
        if self.parameters["max_boron"]['value'] <= self.parameters["max_boron"]['target'] and self.parameters["FDeltaH"]['value'] <= self.parameters["FDeltaH"]['target'] and self.parameters["PinPowerPeaking"]['value'] <= self.parameters["PinPowerPeaking"]['target']:
             fit += self.parameters['cycle_length']['value']*self.parameters['cycle_length']['weight']
        else:
            fit -= max(0,self.parameters["max_boron"]['value']-self.parameters["max_boron"]['target'])*self.parameters['max_boron']['weight']
            fit -= max(0,self.parameters["FDeltaH"]['value']-self.parameters["FDeltaH"]['target'])*self.parameters['FDeltaH']['weight']
            fit -= max(0,self.parameters["PinPowerPeaking"]['value']-self.parameters["PinPowerPeaking"]['target'])*self.parameters['PinPowerPeaking']['weight']
    
        return(fit)

    def get_results(self,filepath,pin_power=False):
        efpd=[]
        boron =[]
        fq=[]
        fdh=[]
        keff = []
        read_bool  = False
        ofile = open(filepath + ".parcs_dpl", "r")
        filestr = ofile.read()
        ofile.close()
        res_str = filestr.split('===============================================================================')
        res_str = res_str[1].split('-------------------------------------------------------------------------------')
        res_str = res_str[0].split('\n')
        for i in range(2, len(res_str)-1):
            res_val=res_str[i].split()
            efpd.append(float(res_val[9]))
            boron.append(float(res_val[14]))
            keff.append(float(res_val[2]))
            fq.append(float(res_val[7]))
            fdh.append(float(res_val[6]))
        res = {}
        self.parameters["cycle_length"]['value'] = self.get_clength(efpd,boron,keff)       
        self.parameters["PinPowerPeaking"]['value'] = max(fq)
        self.parameters["FDeltaH"]['value'] = max(fdh)
        self.parameters["max_boron"]['value'] = max(boron)
        if self.parameters["max_boron"]['value'] == 1800.0:
            max_boron =0
            for i in range(len(boron)):
                if boron[i]== 1800.0:
                    drho_dcb=10 
                    drho = (keff[i]-1.0)*10**5
                    dcb = drho/drho_dcb
                    mboron = 1800.0+dcb
                    if mboron > max_boron:
                        max_boron = mboron
            self.parameters["max_boron"]['value'] = max_boron
            
        lcoe, discharge_bu, asb_cost = self.get_lcoe()
        self.additional_parameters= {}
        self.additional_parameters["LCOE"] = lcoe
        self.additional_parameters["Discharge_Burnup"]=discharge_bu
        self.additional_parameters["Assemblies_Costs"] = asb_cost
        if pin_power:
            zh = np.array([30.48, 30.48, 30.48, 30.48, 30.48, 30.48,
                        30.48, 30.48, 30.48, 30.48, 30.48, 30.48])
            asb_mat=self.get_asb_power(filepath)
            pp_mat = self.get_pin_power(filepath)
            fq_asb = np.max(asb_mat)
            fdh_asb = 0
            for ibu in range(asb_mat.shape[0]):
                for iasb in range(asb_mat.shape[1]):
                    fdh_i = np.dot(asb_mat[ibu,iasb,:],zh)/np.sum(zh)
                    if fdh_i > fdh_asb:
                        fdh_asb = fdh_i
            fq_pp = 0
            fdh_pp = 0
            fq_id = np.array([0,0])
            fdh_id = np.array([0,0])
            for ibu in range(asb_mat.shape[0]):
                for iasb in range(asb_mat.shape[1]):
                    iasb_mat = np.zeros((pp_mat.shape[2],pp_mat.shape[3]))
                    for iz in range(pp_mat.shape[2]):
                        iasb_mat[iz,:]=pp_mat[ibu,iasb,iz,:]
                    fq_i = np.max(iasb_mat)
                    if fq_i > fq_pp:
                        fq_pp = fq_i
                        fq_id[0]=ibu 
                        fq_id[1]=iasb
                    for ip in range(pp_mat.shape[3]):
                        fdh_i = np.dot(iasb_mat[:,ip],zh)/np.sum(zh)
                        if fdh_i > fdh_pp:
                            fdh_pp = fdh_i
                            fdh_id[0]=ibu 
                            fdh_id[1]=iasb
            self.parameters["PinPowerPeaking"]['value'] = fq_pp
            self.parameters["FDeltaH"]['value'] = fdh_pp

    def get_quarter_lattice(self):
            """
            Generates the 17x17 quarter core lattice.

            Parameters: None
        
            Written by Gregory Delipei 7/24/2022
            """
            core_map = self.core_dict['core_map']
            core_id = self.core_dict['core_id']
            nx = int(np.ceil(len(core_map[0])/2))
            ny = int(np.ceil(len(core_map)/2))
            quarter_core = np.zeros((ny,nx), dtype='<U8')
            for y in range(ny):
                for x in range(nx):
                    val =core_map[ny-1+y,nx-1+x]
                    if val is None:
                        val = "00"
                    quarter_core[y,x] = val
            return(quarter_core)

    def get_full_lattice(self):
            """
            Generates the 17x17 quarter core lattice.

            Parameters: None
        
            Written by Gregory Delipei 7/24/2022
            """
            core_map = self.core_dict['core_map']
            core_id = self.core_dict['core_id']
            nx = int(len(core_map[0]))
            ny = int(len(core_map))
            quarter_core = np.zeros((ny,nx), dtype='<U8')
            for y in range(ny):
                for x in range(nx):
                    val =core_map[y,x]
                    if val is None:
                        val = "00"
                    quarter_core[y,x] = val
            return(quarter_core)

    def compute_nasb(self):
        nfa=0
        for x in range(self.core_lattice.shape[0]):
            for y in range(self.core_lattice.shape[1]):
                loc = self.core_lattice[x,y]
                if loc != "00 " and loc != "10 ":
                    nfa+=1
                else:
                    pass
        return(nfa)

    def evaluate(self):
            """
            Creates the input deck, runs the calculation and retrieves the results and the cost.

            Parameters: 
            loc: String - Directory of execution
            fname: String - File name

            Written by Gregory Delipei 7/29/2022
            """

            # Create PARCS INPUT DECK

            pwd = Path(os.getcwd())

            if not os.path.exists(self.name):
                os.makedirs(self.name)
            else:
                shutil.rmtree(self.name, ignore_errors=True)
                os.makedirs(self.name)
            
            cdir = self.library
            shutil.copyfile(cdir + '/' + 'boc_exp_quart193.dep', self.name +"/" + 'boc_exp.dep')
            os.chdir(self.name)
 
            fuel_locations = list(self.core_dict['fuel'].keys())
            self.genome_dict = {}

            for i in range(len(self.genome)):
                self.genome_dict[fuel_locations[i]]=self.genome[i]
                self.core_dict['fuel'][fuel_locations[i]]['Value']=self.genome[i]
                self.core_dict['core'][fuel_locations[i]]['Value']=self.genome[i]

            self.full_core = self.get_full_core()
            if self.map_size == 'quarter':
                self.core_lattice = self.get_quarter_lattice()
            else:
                self.core_lattice = self.get_full_lattice()

            xs_array = np.zeros((self.core_lattice.shape[0],self.core_lattice.shape[1]), dtype='<U20')
            pincal_loc = np.zeros((self.core_lattice.shape[0],self.core_lattice.shape[1]))
            for x in range(self.core_lattice.shape[0]):
                for y in range(self.core_lattice.shape[1]):
                    loc = self.core_lattice[x,y]
                    if loc != "00" and loc[0] != "R":
                        self.core_lattice[x,y] = self.core_dict['Inventory'][self.full_core[loc]]['Tag']
                        xs_array[x,y] = self.core_dict['Inventory'][self.full_core[loc]]['Cross_Section']
                        pincal_loc[x,y]=1
                    elif loc[0] == "R":
                        self.core_lattice[x,y] = "10 "
                        xs_array[x,y] = None
                        pincal_loc[x,y]=0
                    elif loc == "00":
                        self.core_lattice[x,y] = "00 "
                        xs_array[x,y] = None
                        pincal_loc[x,y]=np.nan

            xs_unique = np.unique(xs_array)
            xs_unique = np.delete(xs_unique, np.argwhere(xs_unique == 'None'))

            tag_unique = copy.deepcopy(xs_unique)
            xs_ref = np.arange(4,4+len(xs_unique)) # 1-3 for reflectors
            for key,value in self.core_dict["Inventory"].items():
                for i in range(xs_unique.shape[0]):
                    if value['Cross_Section']==xs_unique[i]:
                        tag_unique[i]=value['Tag']
            fname = 'solution'
            filename = fname + '.inp'
            with open(filename,"w") as ofile:             
                ofile.write("!******************************************************************************\n")
                ofile.write('CASEID {}  \n'.format(fname))
                ofile.write("!******************************************************************************\n\n")

            with open(filename,"a") as ofile:             
                ofile.write("CNTL\n")
                ofile.write("     RUN_OPTS F T F F\n")
                ofile.write("     TH_FDBK    T\n")
                ofile.write("     INT_TH     T -1\n")
                ofile.write("     CORE_POWER 100.0\n")
                ofile.write("     CORE_TYPE  PWR\n")
                ofile.write("     PPM        1000 1.0 1800.0 10.0\n")
                ofile.write("     DEPLETION  T  1.0E-5 T\n")
                ofile.write("     TREE_XS    T  {} T  T  F  F  T  F  T  F  T  F  T  T  T  F \n".format(int(len(xs_unique)+3)))
                ofile.write("     BANK_POS   100 100 100 100 100 100\n")
                ofile.write("     XE_SM      1 1 1 1\n")
                ofile.write("     SEARCH     PPM\n")
                ofile.write("     XS_EXTRAP  1.0 0.3\n")
                ofile.write("     PIN_POWER  T\n")
                ofile.write("     PLOT_OPTS 0 0 0 0 0 2\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")
                
            with open(filename,"a") as ofile:             
                ofile.write("PARAM\n")
                ofile.write("     LSOLVER  1 1 20\n")
                ofile.write("     NODAL_KERN     NEMMG\n")
                ofile.write("     CMFD     2\n")
                ofile.write("     DECUSP   2\n")
                ofile.write("     INIT_GUESS 0\n")
                ofile.write("     CONV_SS   1.e-6 5.e-5 1.e-3 0.001\n")
                ofile.write("     EPS_ERF   0.010\n")
                ofile.write("     EPS_ANM   0.000001\n")
                ofile.write("     NLUPD_SS  5 5 1\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")
            

            with open(filename,"a") as ofile:             
                ofile.write("GEOM\n")
                ofile.write("     GEO_DIM 9 9 14 1 1\n")
                ofile.write("     RAD_CONF\n")
                for x in range(self.core_lattice.shape[0]):
                    ofile.write("     ")
                    for y in range(self.core_lattice.shape[1]):
                        ofile.write(self.core_lattice[x,y])
                        ofile.write("  ")
                    ofile.write("\n")
            
                ofile.write("     GRID_X      1*10.75 8*21.50\n")
                ofile.write("     NEUTMESH_X  1*1 8*1\n")
                ofile.write("     GRID_Y      1*10.75 8*21.50\n")
                ofile.write("     NEUTMESH_Y  1*1 8*1\n")
                ofile.write("     GRID_Z      30.48 12*30.48 30.48\n")            
                ofile.write("     ASSY_TYPE   10   1*2   12*2    1*2 REFL\n")
                for i in range(xs_unique.shape[0]):
                    ofile.write("     ASSY_TYPE   {}   1*1  12*{}  1*3 FUEL\n".format(tag_unique[i],xs_ref[i]))
                ofile.write("\n")
                ofile.write("     boun_cond   0 2 0 2 2 2\n")
                ofile.write("     SYMMETRY 4\n")
                ofile.write("     PINCAL_LOC\n")
                for x in range(pincal_loc.shape[0]):
                    ofile.write("      ")
                    for y in range(pincal_loc.shape[1]):
                        val = pincal_loc[x,y]
                        if np.isnan(val):
                            pass
                        else:
                            ofile.write(str(int(pincal_loc[x,y])))
                            ofile.write("  ")
                    ofile.write("\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")
            
            with open(filename,"a") as ofile:             
                ofile.write("FDBK\n")
                ofile.write("     FA_POWPIT     {} 21.5\n".format(np.round(self.power/193,4)))
                ofile.write("     GAMMA_FRAC    0.0208    0.0    0.0\n")
                ofile.write("     EFF_DOPLT   T  0.5556\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")


            with open(filename,"a") as ofile:   
                ofile.write("TH\n")          
                ofile.write("     FLU_TYP       0\n")
                ofile.write("     N_PINGT    264 25\n")
                ofile.write("     PIN_DIM      4.1 4.75 0.58 6.13\n")
                ofile.write("     FLOW_COND    {}  {}\n".format(np.round(self.inlet_temperature-273.15,2),np.round(self.flow/193,4)))
                ofile.write("     HGAP     11356.0\n")
                ofile.write("     N_RING   6\n")
                ofile.write("     THMESH_X       9*1\n")
                ofile.write("     THMESH_Y       9*1\n")
                ofile.write("     THMESH_Z       1 2 3 4 5 6 7 8 9 10 11 12 13 14\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")

            with open(filename,"a") as ofile:             
                ofile.write("DEPL\n")
                ofile.write("     TIME_STP  1 1 14*30\n")
                ofile.write("     INP_HST   './boc_exp.dep' -2 1\n")
                ofile.write("     PMAXS_F   1 '{}' 1\n".format(cdir + '/' + 'xs_gbot'))
                ofile.write("     PMAXS_F   2 '{}' 2\n".format(cdir + '/' + 'xs_grad'))
                ofile.write("     PMAXS_F   3 '{}' 3\n".format(cdir + '/' + 'xs_gtop'))
                for i in range(xs_unique.shape[0]):
                    ofile.write("     PMAXS_F   {} '{}' {}\n".format(4+i,cdir + '/' + xs_unique[i],4+i))
                ofile.write("\n")
                ofile.write(".")

            # Run PARCS INPUT DECK
            
            parcscmd = "/cm/shared/codes/TRACE51341_PARCS_332/PARCS-v332_Exe/Executables/Linux/parcs-v332-linux2-intel-x64-release.x"
          
            print('Execute PARCS')
            print('Running in process')
            try:
                output = subprocess.check_output([parcscmd, filename], stderr=STDOUT, timeout=50)
                # Get Results
                if 'Finished' in str(output):
                    ofile = fname + '.out'
                    self.get_results(fname,pin_power=True)
                else:
                    self.parameters["cycle_length"]['value'] = np.random.uniform(0,10)
                    self.parameters["PinPowerPeaking"]['value'] = np.random.uniform(10,20)
                    self.parameters["FDeltaH"]['value'] = np.random.uniform(10,20)
                    self.parameters["max_boron"]['value'] = np.random.uniform(2000,5000)
                    self.additional_parameters= {}
                    self.additional_parameters["LCOE"] = 0.0
                    self.additional_parameters["Discharge_Burnup"]=0.0
                    self.additional_parameters["Assemblies_Costs"] = 0.0
        
                os.system('rm -f {}.parcs_pin*'.format(fname))

            except subprocess.TimeoutExpired:
                print('Timed out - killing')
            
                os.system('rm -f {}.parcs_pin*'.format(fname))
                self.parameters["cycle_length"]['value'] = np.random.uniform(0,10)
                self.parameters["PinPowerPeaking"]['value'] = np.random.uniform(10,20)
                self.parameters["FDeltaH"]['value'] = np.random.uniform(10,20)
                self.parameters["max_boron"]['value'] = np.random.uniform(2000,5000)
                self.additional_parameters= {}
                self.additional_parameters["LCOE"] = 0.0
                self.additional_parameters["Discharge_Burnup"]=0.0
                self.additional_parameters["Assemblies_Costs"] = 0.0

            print('{} calculation is done!'.format(self.name))
            os.chdir(pwd)
            gc.collect()  
            print('finished collecting garbage...')
            print('exiting evaluate...')


class MCycle_Loading_Pattern_Solution(Solution):
    """
    Solution class for designing loading patterns using PARCS code.

    Parameters: None

    Written by Gregory Delipei. 01/08/2022
    """
    def __init__(self):
        Solution.__init__(self)
        self.type        = None
        self.number_pins = None
        self.model       = None
        self.symmetry    = None
        self.nrow=17
        self.ncol=17
        self.action_lower=-1
        self.action_upper=1
        self.core_dict={}
       
    def add_additional_information(self,settings):
        """
        Adds information on reactor parameters.

        Parameters
            settings: The settings dictionary for the parameters.
        
        Written by Gregory Delipei. 01/08/2022
        """
        self.symmetry=settings["genome"]["parcs_data"]["symmetry"]
        self.core_dict['core_map'], self.core_dict['core_id'] = self.generate_core()
        if 'inventory' in list(settings["genome"].keys()):
            self.core_dict['Inventory'] = settings["genome"]['inventory']
        else:
            inventory = {}
            for key,value in settings["genome"]["chromosomes"].items():
                inv_it = {}
                inv_it['Max_Limit']=np.inf
                inv_it['In_Design']=0
                inv_it['Cost']=250
                inv_it['Tag']=str(value['type'])
                inv_it['Cross_Section']=value['serial']
                inventory[key]=inv_it
            self.core_dict['Inventory'] = inventory
       
        info = settings['genome']['parcs_data']
        if 'xs_library' in info:
            self.library = info['xs_library']
        if 'power' in info:
            self.power = float(info['power'])
        if 'flow' in info:
            self.flow = float(info['flow'])
        if 'inlet_temperature' in info:
            self.inlet_temperature = float(info['inlet_temperature'])
        if 'map_size' in info:
            self.map_size= info['map_size']
        if 'number_assemblies' in info:
            self.number_assemblies = int(info['number_assemblies'])
        if 'ncycles' in info:
            self.ncycles = int(info['ncycles'])
        if 'fixed_problem' == settings['optimization']['reproducer']:
            self.fixed_genome = True
        elif 'unique_genes' == settings['optimization']['reproducer']:
            self.fixed_genome = True
        self.settings = settings

    def generate_core(self):
        """
        Generates the 17x17 core map with consistent identifiers and treatment of symmetry.

        Parameters: None
        Additional comments:
          - The core_map is manually defined as a list line by line starting from the top of the core.
          It is advised to use the following naming conention for reflector assemblies 'ABCDE' 
          with A being R, BC indicating the row number (00-17) and DE the column number (00-17). For 
          the fuel assemblies it is advised to use the following naming convention 'ABC' with A being the 
          row letter indetifier (A-O) and BC being the column number (00-17). 

        Written by Gregory Delipei 7/12/2022
        """
        core_map = [  None ,  None ,  None ,  None ,"R0004","R0005","R0006","R0007","R0008","R0009","R0010","R0011","R0012",  None ,  None ,  None ,  None ,
                      None ,  None ,"R0102","R0103","R0104", "A05" , "A06" , "A07" , "A08" , "A09" , "A10" , "A11" ,"R0112","R0113","R0114",  None ,  None ,
                      None ,"R0201","R0202", "B03" , "B04" , "B05" , "B06" , "B07" , "B08" , "B09" , "B10" , "B11" , "B12" , "B13" ,"R0214","R0215",  None ,
                      None ,"R0301", "C02" , "C03" , "C04" , "C05" , "C06" , "C07" , "C08" , "C09" , "C10" , "C11" , "C12" , "C13" , "C14" ,"R0315",  None ,
                    "R0400","R0401", "D02" , "D03" , "D04" , "D05" , "D06" , "D07" , "D08" , "D09" , "D10" , "D11" , "D12" , "D13" , "D14" ,"R0415","R0416",
                    "R0500", "E01" , "E02" , "E03" , "E04" , "E05" , "E06" , "E07" , "E08" , "E09" , "E10" , "E11" , "E12" , "E13" , "E14" , "E15" ,"R0516",
                    "R0600", "F01" , "F02" , "F03" , "F04" , "F05" , "F06" , "F07" , "F08" , "F09" , "F10" , "F11" , "F12" , "F13" , "F14" , "F15" ,"R0616",
                    "R0700", "G01" , "G02" , "G03" , "G04" , "G05" , "G06" , "G07" , "G08" , "G09" , "G10" , "G11" , "G12" , "G13" , "G14" , "G15" ,"R0716",
                    "R0800", "H01" , "H02" , "H03" , "H04" , "H05" , "H06" , "H07" , "H08" , "H09" , "H10" , "H11" , "H12" , "H13" , "H14" , "H15" ,"R0816",
                    "R0900", "I01" , "I02" , "I03" , "I04" , "I05" , "I06" , "I07" , "I08" , "I09" , "I10" , "I11" , "I12" , "I13" , "I14" , "I15" ,"R0916",
                    "R1000", "J01" , "J02" , "J03" , "J04" , "J05" , "J06" , "J07" , "J08" , "J09" , "J10" , "J11" , "J12" , "J13" , "J14" , "J15" ,"R1016",
                    "R1100", "K01" , "K02" , "K03" , "K04" , "K05" , "K06" , "K07" , "K08" , "K09" , "K10" , "K11" , "K12" , "K13" , "K14" , "K15" ,"R1116",
                    "R1200","R1201", "L02" , "L03" , "L04" , "L05" , "L06" , "L07" , "L08" , "L09" , "L10" , "L11" , "L12" , "L13" , "L14" ,"R1215","R1216",
                      None ,"R1301", "M02" , "M03" , "M04" , "M05" , "M06" , "M07" , "M08" , "M09" , "M10" , "M11" , "M12" , "M13" , "M14" ,"R1315",  None ,
                      None ,"R1401","R1402", "N03" , "N04" , "N05" , "N06" , "N07" , "N08" , "N09" , "N10" , "N11" , "N12" , "N13" ,"R1414","R1415",  None ,
                      None ,  None ,"R1502","R1503","R1504", "O05" , "O06" , "O07" , "O08" , "O09" , "O10" , "O11" ,"R1512","R1513","R1514",  None ,  None ,
                      None ,  None ,  None ,  None ,"R1604","R1605","R1606","R1607","R1608","R1609","R1610","R1611","R1612",  None ,  None ,  None ,  None ]
        core_map = np.array(core_map).reshape((self.nrow,self.ncol))
        core_id = []
        for i in range(self.nrow-1,-1,-1):
            for j in range(self.ncol):
                core_id.append((i-8,j-8))
        core_id=np.array(core_id).reshape((self.nrow,self.ncol,2))
        if self.symmetry == 'quarter':
            self.symmetry_axes = ((8,8),(8,16),(16,8))
            core, fuel = self.quarter_core(core_map,core_id)
            self.core_dict['core']= {
                'C1': copy.deepcopy(core),
                'C2':copy.deepcopy(core),
                'C3':copy.deepcopy(core)
            }
            self.core_dict['fuel']= {
                'C1': copy.deepcopy(fuel),
                'C2':copy.deepcopy(fuel),
                'C3':copy.deepcopy(fuel)
            }
        elif self.symmetry == 'octant':
            self.symmetry_axes = ((8,8),(16,16),(16,8))
            core, fuel = self.octant_core(core_map,core_id)
            self.core_dict['core']= {
                'C1': copy.deepcopy(core),
                'C2':copy.deepcopy(core),
                'C3':copy.deepcopy(core)
            }
            self.core_dict['fuel']= {
                'C1': copy.deepcopy(fuel),
                'C2':copy.deepcopy(fuel),
                'C3':copy.deepcopy(fuel)
            }
        else:
            raise ValueError(
                f"The selected symmetry ({self.symmetry}) is not valid."
            )
        return(core_map, core_id)

    def get_full_core(self):
        """
        Generates the 17x17 full fuel core from symmetry.

        Parameters: None
    
        Written by Gregory Delipei 7/24/2022
        """
        full_core  = {}
        full_core['C1']  = {}
        full_core['C2']  = {}
        full_core['C3']  = {}
        for key, value in self.core_dict['fuel']['C1'].items():
            full_core['C1'][key]=value['Value']
            for skey in value['Symmetric_Assemblies']:
               full_core['C1'][skey]=value['Value'] 
        for key, value in self.core_dict['fuel']['C2'].items():
            full_core['C2'][key]=value['Value']
            for skey in value['Symmetric_Assemblies']:
               full_core['C2'][skey]=value['Value'] 
        for key, value in self.core_dict['fuel']['C3'].items():
            full_core['C3'][key]=value['Value']
            for skey in value['Symmetric_Assemblies']:
               full_core['C3'][skey]=value['Value'] 
        return(full_core)

    def quarter_core(self,core_map,core_id):
        """
        Generates the quarter core symmetry map.

        Parameters: 
           - core_map: a 17x17 numpy array with the fuel assembly location names.
           - core_id: a 17x17x2 numpy array with coordinate indices for each fuel assembly location
           ranging from -8 to +8.

        Written by Gregory Delipei 7/12/2022
        """
        sym_center = self.symmetry_axes[0]
        sym_horizontal = self.symmetry_axes[1]
        sym_vertical = self.symmetry_axes[2]
        if sym_vertical[0] > sym_center[0]:
            row_iter = np.arange(sym_center[0],sym_vertical[0]+1,1)
        else:
            row_iter = np.arange(sym_center[0],sym_vertical[0]-1,-1)
        if sym_horizontal[1] > sym_center[1]:
            col_iter = np.arange(sym_center[1],sym_horizontal[1]+1,1)
        else:
            col_iter = np.arange(sym_center[1],sym_horizontal[1]-1,-1)

        core_dict={}
        for irow in row_iter:
            for icol in col_iter:
                dict_value={'Symmetric_Assemblies':[],
                            'Value': None}
                if (irow,icol) == sym_center:
                    pass
                elif irow == sym_horizontal[0] and icol != sym_center[1]:                 
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == idy) & (core_id[:,:,1] == -idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0]]
                elif icol == sym_vertical[1] and irow != sym_center[0]:
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0]]
                else:
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    idxy_2= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == -idx))
                    idxy_3= np.where((core_id[:,:,0] == idy) & (core_id[:,:,1] == -idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0], core_map[idxy_2][0], core_map[idxy_3][0]]
                core_dict[core_map[irow,icol]] = dict_value
                fuel_dict = self.extract_fuel(core_dict)
        return(core_dict,fuel_dict)
        
    def octant_core(self, core_map, core_id):
        """
        Generates the octant core symmetry map.

        Parameters: 
           - core_map: a 17x17 numpy array with the fuel assembly location names.
           - core_id: a 17x17x2 numpy array with coordinate indices for each fuel assembly location
           ranging from -8 to +8.

        Written by Gregory Delipei 7/12/2022
        """
        sym_center = self.symmetry_axes[0]
        sym_corner = self.symmetry_axes[1]
        sym_vertical = self.symmetry_axes[2]
        if sym_corner[0] > sym_center[0]:
            row_iter = np.arange(sym_center[0],sym_corner[0]+1,1)
        else:
            row_iter = np.arange(sym_center[0],sym_corner[0]-1,-1)
        if sym_corner[1] > sym_center[1]:
            col_iter = np.arange(sym_center[1],sym_corner[1]+1,1)
        else:
            col_iter = np.arange(sym_center[1],sym_corner[1]-1,-1)

        core_dict={}
        for irow in row_iter:
            for icol in col_iter:
                if icol>irow:
                    continue
                dict_value={'Symmetric_Assemblies':[],
                            'Value': None}
                if (irow,icol) == sym_center:
                    pass
                elif icol == sym_vertical[1] and irow != sym_center[0]:                 
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == idx) & (core_id[:,:,1] == -idy))
                    idxy_2= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    idxy_3= np.where((core_id[:,:,0] == idx) & (core_id[:,:,1] == idy))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0], core_map[idxy_2][0], core_map[idxy_3][0]]
                elif icol == irow and irow != sym_center[0]:
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    idxy_2= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == -idx))
                    idxy_3= np.where((core_id[:,:,0] == idy) & (core_id[:,:,1] == -idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0], core_map[idxy_2][0], core_map[idxy_3][0]]
                else:
                    idy = core_id[irow,icol][0]
                    idx = core_id[irow,icol][1]
                    idxy_1= np.where((core_id[:,:,0] == -idx) & (core_id[:,:,1] == -idy))
                    idxy_2= np.where((core_id[:,:,0] == idx) & (core_id[:,:,1] == -idy))
                    idxy_3= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == idx))
                    idxy_4= np.where((core_id[:,:,0] == -idy) & (core_id[:,:,1] == -idx))
                    idxy_5= np.where((core_id[:,:,0] == idx) & (core_id[:,:,1] == idy))
                    idxy_6= np.where((core_id[:,:,0] == -idx) & (core_id[:,:,1] == idy))
                    idxy_7= np.where((core_id[:,:,0] == idy) & (core_id[:,:,1] == -idx))
                    dict_value['Symmetric_Assemblies'] = [core_map[idxy_1][0], core_map[idxy_2][0], core_map[idxy_3][0], core_map[idxy_4][0],
                                                          core_map[idxy_5][0], core_map[idxy_6][0], core_map[idxy_7][0]]
                core_dict[core_map[irow,icol]] = dict_value
                fuel_dict = self.extract_fuel(core_dict)
        return(core_dict,fuel_dict)

    def extract_fuel(self, core_dict):
        """
        Extracts the unique fuel assemblies from the core in a dictionary.

        Parameters: 
           - core_dict: a core dictionary including all the geometrical parameters.

        Written by Gregory Delipei 7/12/2022
        """
        fuel_dict={}
        for key, value in core_dict.items():
            if key is None:
                continue
            elif key[0]=="R":
                continue
            else:
                fuel_dict[key]=value
        return(fuel_dict)

    def random_design(self):
        """
        Generates a random design following the constraints in the inventory.

        Parameters: None

        Written by Gregory Delipei 7/13/2022
        """

        # Initialization

        avail_locations=list(self.core_dict['fuel'].keys())
        assembly_types = list(self.core_dict['Inventory'].keys())

        for iass in assembly_types:
            self.core_dict['Inventory'][iass]['In_Desing'] = 0

        assembly_types_group = copy.deepcopy(assembly_types)
        avail_locations_group = copy.deepcopy(avail_locations)
        maxiter=10000 # maximum iterations to avoid infinite loop.
        nfuel, nfuel_sym, nrefl, nrefl_sym = self.compute_fa_number()
        total_fuel = nfuel
        total=0

        # Select randomly the fuel assemblies with exact limits in the inventory groups
        for key, value in self.core_dict['Inventory_Groups'].items():
            total_group=0
            if value['Limit']=='Exact':
                niter=0
                while total_group != value['Limit_Value'] and niter<maxiter:
                    avail_choices = []
                    for iloc in avail_locations_group:
                        for iass in value['Values']:
                            proposed_choice = (iloc, iass)
                            symmetry_multiplier = len(self.core_dict['fuel'][iloc]['Symmetric_Assemblies'])+1
                            if (total_group + symmetry_multiplier <= value['Limit_Value']) and (self.core_dict['Inventory'][iass]['In_Design'] <= self.core_dict['Inventory'][iass]['Max_Limit']-symmetry_multiplier):
                                avail_choices.append(proposed_choice)
                    # Re-iterate if the selected random filling strategy cannot meet the inventory limits.
                    if len(avail_choices)==0:
                        total_group=0
                        niter +=1
                        avail_locations_group = copy.deepcopy(avail_locations)
                        for iass in assembly_types_group:
                            self.core_dict['Inventory'][iass]['In_Design'] = 0
                        print(f"New Exact Filling Strategy - {niter}")
                        continue

                    sampled_choice = random.choice(avail_choices)
                    sloc = sampled_choice[0]
                    sass = sampled_choice[1]
                    self.core_dict['fuel'][sloc]['Value']=sass
                    self.core_dict['core'][sloc]['Value']=sass
                    symmetry_multiplier = len(self.core_dict['fuel'][sloc]['Symmetric_Assemblies'])+1
                    self.core_dict['Inventory'][sass]['In_Design']+= symmetry_multiplier
                    avail_locations_group.remove(sloc)
                    total_group+=symmetry_multiplier

                # Update the remaining available quantities for the next inventory groups
                for iass in value['Values']:
                    assembly_types_group.remove(iass)
                avail_locations = copy.deepcopy(avail_locations_group)
                assembly_types=copy.deepcopy(assembly_types_group)
                total+=total_group
        
        # Select randomly the fuel assemblies without exact limits in the inventory groups
        niter=0
        while total != total_fuel and niter<maxiter:
            avail_choices = []
            for iloc in avail_locations:
                for key, value in self.core_dict['Inventory_Groups'].items(): 
                    if value['Limit']!='Exact':
                        subtotal = 0
                        for iass in value["Values"]:
                            subtotal+=self.core_dict['Inventory'][iass]['In_Design']
                        for iass in value["Values"]:
                            proposed_choice = (iloc, iass)
                            symmetry_multiplier = len(self.core_dict['fuel'][iloc]['Symmetric_Assemblies'])+1
                            if (self.core_dict['Inventory'][iass]['In_Design'] <= self.core_dict['Inventory'][iass]['Max_Limit']-symmetry_multiplier) and (subtotal <=value['Limit_Value']-symmetry_multiplier):
                                avail_choices.append(proposed_choice)
      
            # Re-iterate if the selected random filling strategy cannot meet the inventory limits.
            if len(avail_choices)==0:
                total=total_group
                niter +=1
                avail_locations = copy.deepcopy(avail_locations_group)
                for iass in assembly_types:
                    self.core_dict['Inventory'][iass]['In_Desing'] = 0
                print(f"New Filling Strategy - {niter}")
                continue
            sampled_choice = random.choice(avail_choices)
            sloc = sampled_choice[0]
            sass = sampled_choice[1]
            self.core_dict['fuel'][sloc]['Value']=sass
            self.core_dict['core'][sloc]['Value']=sass
            symmetry_multiplier = len(self.core_dict['fuel'][sloc]['Symmetric_Assemblies'])+1
            self.core_dict['Inventory'][sass]['In_Design']+= symmetry_multiplier
            avail_locations.remove(sloc)
            total+=symmetry_multiplier

        return
    
    def action(self,act):
        """
        Performs an action on the current design and updates it.

        Parameters: 
            - act: Dictionary with the action options.

        Written by Gregory Delipei 7/14/2022
        """
        avail_actions = self.get_actions()
        action_location = act['Location']
        action = act['Value']
        act_bounds = np.linspace(self.action_lower,self.action_upper,nact+1)

        if action in avail_actions[action_type][action_location]:
            if action_type =='Exchange':
                loc_value = self.core_dict['core'][action_location]['Value']
                action_value = self.core_dict['core'][action]['Value']
                self.core_dict['core'][action_location]['Value'] = action_value
                self.core_dict['fuel'][action_location]['Value'] = action_value
                self.core_dict['core'][action]['Value'] = loc_value
                self.core_dict['fuel'][action]['Value'] = loc_value
            elif action_type=='Change':
                loc_value = self.core_dict['core'][action_location]['Value']
                loc_symmetry=len(self.core_dict['fuel'][action_location]['Symmetric_Assemblies'])+1
                self.core_dict['core'][action_location]['Value'] = action
                self.core_dict['fuel'][action_location]['Value'] = action
                self.core_dict['Inventory'][loc_value]['In_Design']-=loc_symmetry
                self.core_dict['Inventory'][action]['In_Design']+=loc_symmetry
        else:
            raise ValueError(
                f"The selected action is not valid."
            )
        return

    def mapaction(self,mact):
        """
        Performs an action on the current design and updates it.

        Parameters: 
            - act: Dictionary with the action options.

        Written by Gregory Delipei 7/14/2022
        """
        avail_actions = self.get_actions()
        state = {}
        for key_cycle, values_cycle in self.core_dict["fuel"].items():
            state_values = []
            for key, value in values_cycle.items():
                avail_choices = []
                loc_value = self.core_dict['fuel'][key_cycle][key]['Value']
                state_values.append(loc_value)
            state[key_cycle] = state_values
        action_mvalue = mact['Value']
        action_cycle, action_location = mact['Location']
        action_cycle = 'C' + str(action_cycle)
        loc_actions=avail_actions['Map'][action_cycle][action_location]
        action_space = mact['Space']
        cmap = mact['Action_Map']
        for key,value in loc_actions.items():
            if action_space=="continuous":
                bounds = value['Bounds']
                if bounds[0]<=action_mvalue<bounds[1]:
                    action_type = value['Type']
                    action = value['Value']
                if action_mvalue==bounds[1]==1:
                    action_type = value['Type']
                    action = value['Value']
            elif action_space == "discrete":
                if cmap[value['Value']]==action_mvalue:
                    action = value['Value']
                    if action in state[action_cycle] and action != self.core_dict['fuel'][action_cycle][action_location]['Value'] and action[0:2] !="FE":
                        action_type = 'Exchange'
                        for key_loc, value_loc in self.core_dict["fuel"][action_cycle].items():
                            if value_loc['Value'] == action:
                                action_exchange_loc = key_loc
                    else:
                        action_type = 'Change'
                    
        if action in avail_actions['Actions'][action_cycle][action_location]:
            if action_type =='Exchange':
                loc_value = self.core_dict['core'][action_cycle][action_location]['Value']
                action_value = self.core_dict['core'][action_cycle][action_exchange_loc]['Value']
                self.core_dict['core'][action_cycle][action_location]['Value'] = action_value
                self.core_dict['fuel'][action_cycle][action_location]['Value'] = action_value
                self.core_dict['core'][action_cycle][action_exchange_loc]['Value'] = loc_value
                self.core_dict['fuel'][action_cycle][action_exchange_loc]['Value'] = loc_value
            elif action_type=='Change':
                loc_value = self.core_dict['core'][action_cycle][action_location]['Value']
                loc_symmetry=len(self.core_dict['fuel'][action_cycle][action_location]['Symmetric_Assemblies'])+1
                self.core_dict['core'][action_cycle][action_location]['Value'] = action
                self.core_dict['fuel'][action_cycle][action_location]['Value'] = action
                self.core_dict['Inventory'][loc_value]['In_Design']-=loc_symmetry
                self.core_dict['Inventory'][action]['In_Design']+=loc_symmetry
            new_state = {}
            for key_cycle, values_cycle in self.core_dict['fuel'].items():
                new_state_cycle = {}
                for key, value in values_cycle.items():
                    new_state_cycle[key]=value['Value']
                new_state[key_cycle] = new_state_cycle
            self.set_state(new_state)
        else:
            raise ValueError(
                f"The selected action is not valid."
            )
        return

    def get_actions(self):
        """
        Extracts all possible actions in a dictionary.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """

        # Available actions for every cycle are all assemblies in the inventory
        act = {}
        state = {}
        nact=len(self.core_dict['Inventory'].keys())
        for key_cycle, values_cycle in self.core_dict["fuel"].items():
            act_val = {}
            state_values = []
            for key, value in values_cycle.items():
                avail_choices = []
                loc_value = self.core_dict['fuel'][key_cycle][key]['Value']
                state_values.append(loc_value)
                for key_inv,value_inv in  self.core_dict['Inventory'].items(): 
                    avail_choices.append(key_inv)
                act_val[key] = avail_choices
            state[key_cycle] = state_values
            act[key_cycle]=act_val

        # Create mapping from [0,1] to action and type of action
        map_act = {}
        for key_cycle, values_cycle in self.core_dict["fuel"].items():
            map_act_cycle = {}
            for key, value in values_cycle.items():
                act_bounds = np.linspace(self.action_lower,self.action_upper,nact+1)
                it = 0
                mdict={}
                for i in range(len(act[key_cycle][key])):
                    it+=1
                    adict={}
                    adict['Bounds'] = np.array([act_bounds[it-1],act_bounds[it]])
                    val_act = act[key_cycle][key][i]
                    if val_act[0:2] != 'FE' and val_act in state[key_cycle]:
                        adict['Type'] = 'Exchange'
                    else:
                        adict['Type'] = 'Change'
                    adict['Value'] = val_act
                    mdict['Act'+str(it)] = adict
                map_act_cycle[key]=mdict
            map_act[key_cycle]=map_act_cycle
                
        act_dict={'Actions': act,
                  'Map': map_act}
        return(act_dict)

    def get_mapstate(self,cmap,observation_type):
        """
        Gets the current state in a normalized format.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """
        ncycles = len(self.core_dict['fuel'].keys())
        ncass =  len(self.core_dict['fuel']['C1'].keys())
        nass = ncycles*ncass
        if observation_type=='continuous':
            mstate=np.zeros(nass,dtype=np.int8)
        elif observation_type=='multi_discrete':
            mstate=np.zeros(nass+1,dtype=np.int8)
        it=0
        for key_cycle, value_cycle in self.core_dict['fuel'].items():
            for key, value in value_cycle.items():
                mstate[it]=cmap[value['Value']]
                it+=1
        return(mstate)

    def get_inventory_group(self,iass):
        """
        Get in which group an assembly belongs to.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """
        igroup = None
        for key,value in self.core_dict['Inventory_Groups'].items():
            if iass in value['Values']:
                igroup = key
        return(igroup)
    
    def get_group_indesign(self,group):
        """
        Get in which group an assembly belongs to.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """
        sum_in = 0
        for iass in self.core_dict['Inventory_Groups'][group]['Values']:
            sum_in += self.core_dict['Inventory'][iass]['In_Design']
        return(sum_in)

    def plot_design(self,filepath):
        """
        Plot current loading pattern design.

        Parameters: None

        Written by Gregory Delipei 7/13/2022
        """
        color_fill = ['maroon','red','darkorange','limegreen','turquoise','pink','purple','plum','teal']
        nfa = 1
        tags=[]
        for key in self.core_dict['Inventory'].keys():
            if self.core_dict['Inventory'][key]['In_Design'] > 0:
                nfa+=1
                tags.append(key)
        ass_pitch = 21.21      

        plt.rcParams.update({'font.size': 4})
        fig=plt.figure()
        plt.axes()

        value_map = copy.deepcopy(self.core_dict['core_map'])
        value_map = value_map.astype('<U12')
        for key, value in self.core_dict['core'].items():
            value_map[np.where(self.core_dict['core_map']==key)] = value['Value']
            for isym in value['Symmetric_Assemblies']:
                value_map[np.where(self.core_dict['core_map']==isym)] = value['Value']

        for i in range(17):
            for j in range(17):
                ass_type=value_map[i,j]
                yloc=self.core_dict['core_id'][i,j][0]
                xloc=self.core_dict['core_id'][i,j][1]
                yid = yloc*ass_pitch
                xid = xloc*ass_pitch
                if ass_type == 'None':
                    continue
                else:
                    ass_color = color_fill[tags.index(ass_type)]
                    rectangle = plt.Rectangle((xid,yid),ass_pitch, ass_pitch,fc=ass_color,ec='grey')
                    plt.gca().add_patch(rectangle)
                    plt.text(xid+5,yid+9,self.core_dict['core_map'][i,j])


        plt.rcParams.update({'font.size': 8})
        rectangle = plt.Rectangle((12*ass_pitch,8*ass_pitch),0.3*ass_pitch,0.2*ass_pitch,1,fc="White")
        plt.gca().add_patch(rectangle)
        for i in range(len(tags)):    
            rectangle = plt.Rectangle((9.0*ass_pitch,8*ass_pitch-i*ass_pitch),0.4*ass_pitch,0.3*ass_pitch,1,fc=color_fill[i])
            plt.gca().add_patch(rectangle)
            plt.text(9.5*ass_pitch,8*ass_pitch-i*ass_pitch-0.03*ass_pitch,tags[i])

        plt.axis('scaled')
        plt.tick_params(left = False, right = False , labelleft = False ,
                        labelbottom = False, bottom = False)

        plt.savefig(filepath,bbox_inches='tight',dpi=300) 
        plt.close(fig)

    def compute_fa_number(self):
        """
        Computes the total number of fuel/reflector assemblies in the core with and without symmetry.

        Parameters: None

        Written by Gregory Delipei 7/14/2022
        """
        nfuel=0
        nfuel_sym=0
        nrefl = 0
        nrefl_sym = 0
        for key, value in self.core_dict['core'].items():
            symmetry_multiplier = len(self.core_dict['core'][key]['Symmetric_Assemblies'])+1
            if key is None:
                continue
            elif key[0]=='R':
                nrefl_sym+=1
                nrefl+=symmetry_multiplier
            else:
                nfuel_sym+=1
                nfuel+=symmetry_multiplier
        return(nfuel,nfuel_sym,nrefl,nrefl_sym)

        return
    
    def set_state(self,state):
        
        for key,value in self.core_dict['Inventory'].items():
            nvalue = value['In_Design']=0
            self.core_dict['Inventory'][key] = value

        for key_cycle, values_cycle in state.items():
            for key, value in values_cycle.items():
                symmetry_multiplier = len(self.core_dict['fuel'][key_cycle][key]['Symmetric_Assemblies'])+1
                self.core_dict['fuel'][key_cycle][key]['Value']=value
                self.core_dict['core'][key_cycle][key]['Value']=value
                self.core_dict['Inventory'][value]['In_Design']+=symmetry_multiplier
        return

    def get_state(self):
        state={}
        for key, value in self.core_dict['fuel'].items():
            state[key]=value['Value']
        return(state)
    
    def genes_in_group(self,chromosome_map,group_name):
        """
        Returns a list of the genes in the chosen group
        """
        gene_list = []
        for gene in chromosome_map:
            if gene == 'symmetry_list':
                pass
            else:
                if group_name == chromosome_map[gene]['gene_group']:
                    gene_list.append(gene)

        return gene_list

    def is_gene_ok(self,chromosome_map,gene,space):
        """
        Checks if the gene is allowed in the desired location
        """
        gene_is_ok = True
        if not chromosome_map[gene]['map'][space]:
            gene_is_ok = False
        if space in chromosome_map['symmetry_list']:
            if self.my_group[chromosome_map[gene]['gene_group']] <= 1:
                gene_is_ok = False
        else:
            if not self.my_group[chromosome_map[gene]['gene_group']]:
                gene_is_ok = False
        if 'unique' in chromosome_map[gene]:
            if gene in self.genome:
                gene_is_ok = False

        return gene_is_ok

    def generate_initial(self,chromosome_map):
        """
        Generates the initial solutions to the optimization problem.

        Parameters: 
            chromosome_map: Dictionary
                The genome portion of the dictionary settings file. 

        Written by Brian Andersen. 1/9/2020
        """
        chromosome_length = None
        chromosome_list = list(chromosome_map.keys())
        if 'symmetry_list' in chromosome_list:
            chromosome_list.remove('symmetry_list')

        for chromosome in chromosome_list:
            if chromosome_length is None:
                chromosome_length = len(chromosome_map[chromosome]['map'])
            elif len(chromosome_map[chromosome]['map']) == chromosome_length:
                pass
            else:
                raise ValueError("Chromosome Maps are of unequal length")

        fresh_fuel_list = []
        burnt_fuel_list = []
        self.genome = []
        # Separate fresh from burnt assemblies
        for i in range(len(chromosome_list)):
            if chromosome_list[i] in self.core_dict['fuel']['C1'].keys():
                burnt_fuel_list.append(chromosome_list[i]) 
            else:
                fresh_fuel_list.append(chromosome_list[i]) 
        
        fuel_types =  ['Fresh', 'Burnt']
        for ci in range(self.ncycles):   
            burnt_fuel_cycle_list = copy.deepcopy(burnt_fuel_list)                                         
            for i in range(chromosome_length):              
                no_gene_found = True                        
                while no_gene_found:
                    gene_type = random.choice(fuel_types)
                    if gene_type == 'Fresh':
                        gene = random.choice(fresh_fuel_list)
                    else:
                        gene = random.choice(burnt_fuel_cycle_list)
                    if chromosome_map[gene]['map'][i]:
                        self.genome.append(gene)
                        if gene in burnt_fuel_cycle_list:
                            burnt_fuel_cycle_list.remove(gene)
                        no_gene_found = False
        
    def generate_initial_fixed(self,chromosome_map,gene_groups):
        """
        Generates initial solution when only specific number of assemblies
        may be used.

        Written by Brian Andersen 3/15/2020
        """
        chromosome_length = None
        chromosome_list = list(chromosome_map.keys())
        if 'symmetry_list' in chromosome_list:
            chromosome_list.remove('symmetry_list')

        for chromosome in chromosome_list:
            if chromosome_length is None:
                chromosome_length = len(chromosome_map[chromosome]['map'])
            elif len(chromosome_map[chromosome]['map']) == chromosome_length:
                pass
            else:
                raise ValueError("Chromosome Maps are of unequal length")

        no_valid_solution = True
        while no_valid_solution:
            no_valid_solution = False
            my_group = copy.deepcopy(gene_groups)
            self.genome = [None]*chromosome_length
            for i in range(chromosome_length):
                no_gene_found = True
                attempt_counter = 0
                while no_gene_found:
                    gene = random.choice(chromosome_list)
                    if 'unique' in chromosome_map[gene]:
                        if chromosome_map[gene]['unique']:
                            if gene in self.genome:
                                pass
                            else:
                                #This else loop activates if the gene is labeled unique but is not used. 
                                if chromosome_map[gene]['map'][i] == 1:
                                    if i in chromosome_map['symmetry_list']:
                                        if my_group[chromosome_map[gene]['gene_group']] > 1:
                                            self.genome[i] = gene
                                            no_gene_found = False
                                            my_group[chromosome_map[gene]['gene_group']] -= 2
                                    else:
                                        if my_group[chromosome_map[gene]['gene_group']] > 0:
                                            self.genome[i] = gene
                                            no_gene_found = False
                                            my_group[chromosome_map[gene]['gene_group']] -= 1            
                        else:
                            #adding unique loop above this code
                            if chromosome_map[gene]['map'][i] == 1:
                                if i in chromosome_map['symmetry_list']:
                                    if my_group[chromosome_map[gene]['gene_group']] > 1:
                                        self.genome[i] = gene
                                        no_gene_found = False
                                        my_group[chromosome_map[gene]['gene_group']] -= 2
                                else:
                                    if my_group[chromosome_map[gene]['gene_group']] > 0:
                                        self.genome[i] = gene
                                        no_gene_found = False
                                        my_group[chromosome_map[gene]['gene_group']] -= 1
                    else:
                        #adding unique loop above this code
                        if chromosome_map[gene]['map'][i] == 1:
                            if i in chromosome_map['symmetry_list']:
                                if my_group[chromosome_map[gene]['gene_group']] > 1:
                                    self.genome[i] = gene
                                    no_gene_found = False
                                    my_group[chromosome_map[gene]['gene_group']] -= 2
                            else:
                                if my_group[chromosome_map[gene]['gene_group']] > 0:
                                    self.genome[i] = gene
                                    no_gene_found = False
                                    my_group[chromosome_map[gene]['gene_group']] -= 1
                    attempt_counter += 1
                    if attempt_counter == 100:
                        no_gene_found = False
                        no_valid_solution = True

    def new_generate_initial_fixed(self,chromosome_map,gene_groups):
        """
        Generates initial solution when only speciific number of assemblies may be used.

        Written by Brian Andersen 3/15/2020. Last edited 11/20/2020
        """
        #above here is the old code
        chromosome_length = None
        chromosome_list = list(chromosome_map.keys())
        if 'symmetry_list' in chromosome_list:
            chromosome_list.remove('symmetry_list')

        for chromosome in chromosome_list:
            if chromosome_length is None:
                chromosome_length = len(chromosome_map[chromosome]['map'])
            elif len(chromosome_map[chromosome]['map']) == chromosome_length:
                pass
            else:
                raise ValueError("Chromosome Maps are of unequal length")

        no_genome_found = True
        while no_genome_found:
            attempts = 0
            self.my_group = copy.deepcopy(gene_groups)
            self.genome = [None]*chromosome_length
            unfilled_spaces = list(range(chromosome_length))
            while unfilled_spaces:  
                space_number = random.randint(0,len(unfilled_spaces)-1)
                group_name = None
                while not group_name:
                    random_group = random.choice(list(self.my_group.keys()))
                    if self.my_group[random_group] > 0:
                        group_name = random_group
                available_gene_list = self.genes_in_group(chromosome_map,group_name)
                space = unfilled_spaces[space_number]
                gene = random.choice(available_gene_list)
                gene_is_ok = self.is_gene_ok(chromosome_map,gene,space)
                if gene_is_ok:
                    self.genome[space] = gene
                    unfilled_spaces.remove(space)
                    if space in chromosome_map['symmetry_list']:
                        self.my_group[chromosome_map[gene]['gene_group']] -= 2
                    else:
                        self.my_group[chromosome_map[gene]['gene_group']] -= 1             
                else:
                    attempts += 1
                if attempts == 100:
                    break

            bad_gene_list = []
            for i,gene in enumerate(self.genome):
                if not gene:
                    bad_gene_list.append(i)

            if not bad_gene_list:
                no_genome_found = False                

    def get_clength(self,efpd,boron,keff):
        if 0.1 in boron:
            eoc1_ind = 0
            eco2_ind = 0
            first_appear = False # bolean to identify boron=0.1 first appearance
            for i in range(len(efpd)-1):
                if boron[i] > 0.1 and boron[i+1] == 0.1 and first_appear == False:
                    eoc1_ind = i
                    eco2_ind = i+1
                    first_appear = True
            dbor = abs(boron[eoc1_ind-1]-boron[eoc1_ind])
            defpd = abs(efpd[eoc1_ind-1]-efpd[eoc1_ind])
            if dbor == 0 or eoc1_ind==0:
                def_dbor = 0.0
            else:
                def_dbor = defpd/dbor
            eoc = efpd[eoc1_ind] + def_dbor*(boron[eoc1_ind]-0.1)
            eoc = min(eoc, efpd[eoc1_ind+1])
        elif boron[-1]==boron[0]==1800.0:
            drho_dcb=10 
            drho1 = (keff[-2]-1.0)*10**5
            dcb1 = drho1/drho_dcb
            cb1= boron[-2] + dcb1
            drho2 = (keff[-1]-1.0)*10**5
            dcb2 = drho2/drho_dcb
            cb2= boron[-1] + dcb2
            dbor = abs(cb1-cb2)
            defpd = abs(efpd[-2]-efpd[-1])
            def_dbor = defpd/dbor
            eoc = efpd[-1] + def_dbor*(cb2-0.1)
        else:
            dbor = abs(boron[-2]-boron[-1])
            defpd = abs(efpd[-2]-efpd[-1])
            if dbor == 0:
                def_dbor = 0
            else:
                def_dbor = defpd/dbor
            eoc = efpd[-1] + def_dbor*(boron[-1]-0.1)
        if eoc == 0.0:
            eoc += 0.1
        return(eoc)

    def get_max_boron(self,boron,keff):
        res = max(boron)
        if res == 1800.0:
            max_boron =0
            for i in range(len(boron)):
                if boron[i]== 1800.0:
                    drho_dcb=10 
                    drho = (keff[i]-1.0)*10**5
                    dcb = drho/drho_dcb
                    mboron = 1800.0+dcb
                    if mboron > max_boron:
                        max_boron = mboron
            res = max_boron
        return(res)

    def get_pin_power(self,filepath):
        start = time.time()
        print('Reading of Pin Powers')
        npx=17
        npy=17
        npin = npx*npy
        nbu = 17
        nz=16
        nasb = self.compute_nasb()
        pp_mat = np.zeros((nbu,nasb,nz,npin))
        for iasb in range(nasb):
            pinfile = filepath + ".parcs_pin" + str(iasb+1).zfill(3)
            ofile = open(pinfile, "r")
            filestr = ofile.read()
            ofile.close()
            asbstr = filestr.split('  Case:')
            for i in range(1,len(asbstr)):
                asb_line =asbstr[i].split('\n')
                ibu=int(asb_line[0][0:4])-1
                iz_val = int(asb_line[0][66:68])
                if iz_val == 0:
                    continue
                else:
                    iz = iz_val-2
                    pp_str = asb_line[2:2+npy]
                    for iy in range(npy):
                        for ix in range(npx):
                            pp_id = iy*npx + ix 
                            try:
                                pp_mat[ibu,iasb,iz,pp_id] = float(pp_str[iy][(7*ix + 8):(7*ix + 14)])
                            except:
                                print("Non physical peaking factors")
                                pp_mat[ibu,iasb,iz,pp_id] = 10.0

        end = time.time()
        print('Pin Power Duration = {} s'.format(end-start))
        return(pp_mat)

    def get_asb_power(self,filepath):
        start = time.time()
        print('Reading of Assembly Powers')
        ofile = open(filepath+".parcs_dep", "r")
        filestr = ofile.read()
        ofile.close()
        bustr=filestr.split(" RPF 3D MAP")
        nbu= len(bustr)-1
        nz_str = bustr[0].split(' RPF 1D MAP')[1].split('\n')
        nrefl=2
        nz = len(nz_str)-4-nrefl
        ztag = np.arange(2,nz+1 + 1)
        nasb = self.compute_nasb()
        asb_mat = np.zeros((nbu,nasb,nz))
        for ibu in range(nbu):
            ibustr = bustr[ibu+1].split(' EXP 2D MAP')[0]
            asb_str = ibustr.split(' k lb')
            iasb=0
            for ik in range(1,len(asb_str)):
                asb_line=asb_str[ik].split('\n')
                for iz in range(1,len(asb_line)):
                    asb_val=asb_line[iz].split()
                    if len(asb_val)>0:
                        if int(asb_val[0]) in ztag:
                            zid = int(asb_val[0])-2
                            asb_count = 0
                            for ia in range(1,len(asb_val)):
                                val = float(asb_val[ia])
                                if  val !=0.0:
                                    asb_id = iasb + asb_count
                                    asb_mat[ibu,asb_id,zid]=val
                                    asb_count+=1
                                else:
                                    continue
                    else:
                        continue
                iasb += asb_count
        end = time.time()
        print('Assembly Power Duration = {} s'.format(end-start))
        return(asb_mat)

    def get_lcoe(self):
        
        cycle1_param={'EFPD': self.parameters['cycle1_length']['value'],
                    'Batches': 3,
                    'Thermal_Power': self.power,
                    'Efficiency': 0.33,
                    'Fuel_Assemblies': self.number_assemblies}

        lcoe_param={'Discount_Rate': 0.07,
                    'Uranium_Ore_Price': 80,
                    'Conversion_Price': 10,
                    'Enrichment_Price': 160,
                    'Fabrication_Price': 250,
                    'Uranium_Ore_Loss': 0.002,
                    'Conversion_Loss': 0.002,
                    'Enrichment_Loss': 0.002,
                    'Fabrication_Loss': 0.002,
                    'Enrichment_Feed': 0.00711,
                    'Enrichment_Tail': 0.003,
                    'Storage_Price': 200,
                    'Disposal_Price': 463,
                    'Uranium_Ore_Time': -2.0,
                    'Conversion_Time': -1.5,
                    'Enrichment_Time': -1.0,
                    'Fabrication_Time': -0.5,
                    'Storage_Time': 5.0+cycle1_param['EFPD']*cycle1_param['Batches']/365.25,
                    'Disposal_Time': cycle1_param['EFPD']*cycle1_param['Batches']/365.25}

        as_values=list(self.full_core['C1'].values())
        for i in range(len(as_values)):
            elt = as_values[i]
            if elt in self.core_dict['fuel']['C1']:
                as_values[i]='BRN'

        unique_fa =  np.unique(as_values)
        asb_param = {}
        for i in range(len(unique_fa)):
            nfa = as_values.count(unique_fa[i])
            if unique_fa[i] == 'BRN':
                enr = 0.01
                asb_dict = {'Number': nfa,
                            'Fuel_Rods': 264,
                            'Fuel_Radius': 0.41,
                            'Fuel_Height': 365.76,
                            'Enrichment': enr,
                            'Fuel_Density': 10.23,
                            'Fabrication_Price': 0.0
                            }
            else:
                enr = float(unique_fa[i][2:5])/10000
                asb_dict = {'Number': nfa,
                            'Fuel_Rods': 264,
                            'Fuel_Radius': 0.41,
                            'Fuel_Height': 365.76,
                            'Enrichment': enr,
                            'Fuel_Density': 10.23,
                            'Fabrication_Price': 250
                            }
            asb_param[unique_fa[i]]=asb_dict

        lcoe_c1, bu, asb_cost = LCOE_MCYC(cycle1_param,lcoe_param, asb_param)

        cycle2_param={'EFPD': self.parameters['cycle2_length']['value'],
                    'Batches': 3,
                    'Thermal_Power': self.power,
                    'Efficiency': 0.33,
                    'Fuel_Assemblies': self.number_assemblies}

        lcoe2_param={'Discount_Rate': 0.07,
                    'Uranium_Ore_Price': 80,
                    'Conversion_Price': 10,
                    'Enrichment_Price': 160,
                    'Fabrication_Price': 250,
                    'Uranium_Ore_Loss': 0.002,
                    'Conversion_Loss': 0.002,
                    'Enrichment_Loss': 0.002,
                    'Fabrication_Loss': 0.002,
                    'Enrichment_Feed': 0.00711,
                    'Enrichment_Tail': 0.003,
                    'Storage_Price': 200,
                    'Disposal_Price': 463,
                    'Uranium_Ore_Time': -2.0 + cycle1_param['EFPD']/365.25,
                    'Conversion_Time': -1.5 + cycle1_param['EFPD']/365.25,
                    'Enrichment_Time': -1.0 + cycle1_param['EFPD']/365.25,
                    'Fabrication_Time': -0.5 + cycle1_param['EFPD']/365.25,
                    'Storage_Time': 5.0+ cycle1_param['EFPD']/365.25 +cycle2_param['EFPD']*cycle2_param['Batches']/365.25,
                    'Disposal_Time': cycle1_param['EFPD']/365.25 + cycle2_param['EFPD']*cycle2_param['Batches']/365.25}

        as_values=list(self.full_core['C2'].values())
        for i in range(len(as_values)):
            elt = as_values[i]
            if elt in self.core_dict['fuel']['C2']:
                as_values[i]='BRN'

        unique_fa =  np.unique(as_values)
        asb2_param = {}
        for i in range(len(unique_fa)):
            nfa = as_values.count(unique_fa[i])
            if unique_fa[i] == 'BRN':
                enr = 0.01
                asb_dict = {'Number': nfa,
                            'Fuel_Rods': 264,
                            'Fuel_Radius': 0.41,
                            'Fuel_Height': 365.76,
                            'Enrichment': enr,
                            'Fuel_Density': 10.23,
                            'Fabrication_Price': 0.0
                            }
            else:
                enr = float(unique_fa[i][2:5])/10000
                asb_dict = {'Number': nfa,
                            'Fuel_Rods': 264,
                            'Fuel_Radius': 0.41,
                            'Fuel_Height': 365.76,
                            'Enrichment': enr,
                            'Fuel_Density': 10.23,
                            'Fabrication_Price': 250
                            }
            asb2_param[unique_fa[i]]=asb_dict

        lcoe_c2, bu, asb_cost = LCOE_MCYC(cycle2_param,lcoe2_param, asb2_param)

        cycle3_param={'EFPD': self.parameters['cycle3_length']['value'],
                    'Batches': 3,
                    'Thermal_Power': self.power,
                    'Efficiency': 0.33,
                    'Fuel_Assemblies': self.number_assemblies}

        lcoe3_param={'Discount_Rate': 0.07,
                    'Uranium_Ore_Price': 80,
                    'Conversion_Price': 10,
                    'Enrichment_Price': 160,
                    'Fabrication_Price': 250,
                    'Uranium_Ore_Loss': 0.002,
                    'Conversion_Loss': 0.002,
                    'Enrichment_Loss': 0.002,
                    'Fabrication_Loss': 0.002,
                    'Enrichment_Feed': 0.00711,
                    'Enrichment_Tail': 0.003,
                    'Storage_Price': 200,
                    'Disposal_Price': 463,
                    'Uranium_Ore_Time': -2.0 + cycle1_param['EFPD']/365.25 + cycle2_param['EFPD']/365.25,
                    'Conversion_Time': -1.5 + cycle1_param['EFPD']/365.25 + cycle2_param['EFPD']/365.25,
                    'Enrichment_Time': -1.0 + cycle1_param['EFPD']/365.25 + cycle2_param['EFPD']/365.25,
                    'Fabrication_Time': -0.5 + cycle1_param['EFPD']/365.25 + cycle2_param['EFPD']/365.25,
                    'Storage_Time': 5.0 + cycle1_param['EFPD']/365.25 + cycle2_param['EFPD']/365.25 +cycle3_param['EFPD']*cycle3_param['Batches']/365.25,
                    'Disposal_Time': cycle1_param['EFPD']/365.25 + cycle2_param['EFPD']/365.25 + cycle3_param['EFPD']*cycle3_param['Batches']/365.25}

        as_values=list(self.full_core['C3'].values())
        for i in range(len(as_values)):
            elt = as_values[i]
            if elt in self.core_dict['fuel']['C3']:
                as_values[i]='BRN'

        unique_fa =  np.unique(as_values)
        asb3_param = {}
        for i in range(len(unique_fa)):
            nfa = as_values.count(unique_fa[i])
            if unique_fa[i] == 'BRN':
                enr = 0.01
                asb_dict = {'Number': nfa,
                            'Fuel_Rods': 264,
                            'Fuel_Radius': 0.41,
                            'Fuel_Height': 365.76,
                            'Enrichment': enr,
                            'Fuel_Density': 10.23,
                            'Fabrication_Price': 0.0
                            }
            else:
                enr = float(unique_fa[i][2:5])/10000
                asb_dict = {'Number': nfa,
                            'Fuel_Rods': 264,
                            'Fuel_Radius': 0.41,
                            'Fuel_Height': 365.76,
                            'Enrichment': enr,
                            'Fuel_Density': 10.23,
                            'Fabrication_Price': 250
                            }
            asb3_param[unique_fa[i]]=asb_dict

        lcoe_c3, bu, asb_cost = LCOE(cycle3_param,lcoe3_param, asb3_param)
        return((lcoe_c1, lcoe_c2, lcoe_c3))

    def get_results(self,filepath,pin_power=False):
        efpd_c1=[]
        efpd_c2=[]
        efpd_c3=[]
        boron_c1 =[]
        boron_c2 =[]
        boron_c3 =[]
        fq=[]
        fdh=[]
        keff_c1 = []
        keff_c2 = []
        keff_c3 = []
        read_bool  = False
        ofile = open(filepath + ".parcs_dpl", "r")
        filestr = ofile.read()
        ofile.close()
        res_str = filestr.split('===============================================================================')
        
        res_str1 = res_str[2].split('-------------------------------------------------------------------------------')
        res_str1 = res_str1[0].split('\n')
        for i in range(2, len(res_str1)-1):
            res_val=res_str1[i].split()
            efpd_c1.append(float(res_val[9]))
            boron_c1.append(float(res_val[14]))
            keff_c1.append(float(res_val[2]))
            fq.append(float(res_val[7]))
            fdh.append(float(res_val[6]))

        res_str2 = res_str[3].split('-------------------------------------------------------------------------------')
        res_str2 = res_str2[0].split('\n')
        for i in range(2, len(res_str2)-1):
            res_val=res_str2[i].split()
            efpd_c2.append(float(res_val[9]))
            boron_c2.append(float(res_val[14]))
            keff_c2.append(float(res_val[2]))
            fq.append(float(res_val[7]))
            fdh.append(float(res_val[6]))
        res_str3 = res_str[4].split('-------------------------------------------------------------------------------')
        res_str3 = res_str3[0].split('\n')
        for i in range(2, len(res_str3)-1):
            res_val=res_str3[i].split()
            efpd_c3.append(float(res_val[9]))
            boron_c3.append(float(res_val[14]))
            keff_c3.append(float(res_val[2]))
            fq.append(float(res_val[7]))
            fdh.append(float(res_val[6]))
        res = {}
        self.parameters["cycle1_length"]['value'] = self.get_clength(efpd_c1,boron_c1,keff_c1)
        self.parameters["cycle2_length"]['value'] = self.get_clength(efpd_c2,boron_c2,keff_c2)
        self.parameters["cycle3_length"]['value'] = self.get_clength(efpd_c3,boron_c3,keff_c3)       
        self.parameters["PinPowerPeaking"]['value'] = max(fq)
        self.parameters["FDeltaH"]['value'] = max(fdh)
        mbor_c1 = self.get_max_boron(boron_c1,keff_c1)
        mbor_c2 = self.get_max_boron(boron_c2,keff_c2)
        mbor_c3 = self.get_max_boron(boron_c3,keff_c3)
        self.parameters["max_boron"]['value'] = max([mbor_c1,mbor_c2,mbor_c3])    
        lcoe1, lcoe2, lcoe3 = self.get_lcoe()
        lcoe = (lcoe1 + lcoe2 + lcoe3)/3
        self.parameters["lcoe"]['value'] = lcoe

        if pin_power:
            zh = np.array([15.24, 10.16, 5.08, 30.48, 30.48, 30.48, 30.48, 30.48,
                        30.48, 30.48, 30.48, 30.48, 30.48, 5.08, 10.16, 15.24])
            asb_mat=self.get_asb_power(filepath)
            pp_mat = self.get_pin_power(filepath)
            fq_asb = np.max(asb_mat)
            fdh_asb = 0
            for ibu in range(asb_mat.shape[0]):
                for iasb in range(asb_mat.shape[1]):
                    fdh_i = np.dot(asb_mat[ibu,iasb,:],zh)/np.sum(zh)
                    if fdh_i > fdh_asb:
                        fdh_asb = fdh_i
            fq_pp = 0
            fdh_pp = 0
            fq_id = np.array([0,0])
            fdh_id = np.array([0,0])
            for ibu in range(asb_mat.shape[0]):
                for iasb in range(asb_mat.shape[1]):
                    iasb_mat = np.zeros((pp_mat.shape[2],pp_mat.shape[3]))
                    for iz in range(pp_mat.shape[2]):
                        iasb_mat[iz,:]=pp_mat[ibu,iasb,iz,:]
                    fq_i = np.max(iasb_mat)
                    if fq_i > fq_pp:
                        fq_pp = fq_i
                        fq_id[0]=ibu 
                        fq_id[1]=iasb
                    for ip in range(pp_mat.shape[3]):
                        fdh_i = np.dot(iasb_mat[:,ip],zh)/np.sum(zh)
                        if fdh_i > fdh_pp:
                            fdh_pp = fdh_i
                            fdh_id[0]=ibu 
                            fdh_id[1]=iasb
            self.parameters["PinPowerPeaking"]['value'] = fq_pp
            self.parameters["FDeltaH"]['value'] = fdh_pp

    def get_quarter_lattice(self):
            """
            Generates the 17x17 quarter core lattice.

            Parameters: None
        
            Written by Gregory Delipei 7/24/2022
            """
            core_map = self.core_dict['core_map']
            core_id = self.core_dict['core_id']
            nx = int(np.ceil(len(core_map[0])/2))
            ny = int(np.ceil(len(core_map)/2))
            quarter_core = np.zeros((ny,nx), dtype='<U8')
            for y in range(ny):
                for x in range(nx):
                    val =core_map[ny-1+y,nx-1+x]
                    if val is None:
                        val = "00"
                    quarter_core[y,x] = val
            return(quarter_core)

    def get_full_lattice(self):
            """
            Generates the 17x17 quarter core lattice.

            Parameters: None
        
            Written by Gregory Delipei 7/24/2022
            """
            core_map = self.core_dict['core_map']
            core_id = self.core_dict['core_id']
            nx = int(len(core_map[0]))
            ny = int(len(core_map))
            quarter_core = np.zeros((ny,nx), dtype='<U8')
            for y in range(ny):
                for x in range(nx):
                    val =core_map[y,x]
                    if val is None:
                        val = "00"
                    quarter_core[y,x] = val
            return(quarter_core)

    def compute_nasb(self):
        nfa=0
        for x in range(self.core_lattice.shape[0]):
            for y in range(self.core_lattice.shape[1]):
                loc = self.core_lattice[x,y]
                if loc != "00 " and loc != "10 ":
                    nfa+=1
                else:
                    pass
        return(nfa)

    def reproduce(self):
        old_genome = self.genome
        new_genome = copy.deepcopy(old_genome)
        nfuel = len(self.core_dict['fuel']['C1'].keys())
        cyc_id=random.choice([1, 2, 3])
        pos_id = random.choice(np.arange(nfuel)) + (cyc_id-1)*nfuel
        cyc_genome = old_genome[(cyc_id-1)*56:(cyc_id)*56]
        inv = list(self.core_dict['Inventory'].keys())
        old_gene = old_genome[pos_id]
        inv.remove(old_gene)
        burnt_fuel_list = []
        fresh_fuel_list = []
        for i in range(len(inv)):
            if inv[i] in self.core_dict['fuel']['C1'].keys():
                burnt_fuel_list.append(inv[i]) 
            else:
                fresh_fuel_list.append(inv[i])
        new_gene = random.choice(inv)
        if new_gene in burnt_fuel_list and new_gene in cyc_genome:
            cgen_id = np.where(np.array(cyc_genome)==new_gene)[0][0] + (cyc_id-1)*nfuel
            new_genome[pos_id] = new_gene
            new_genome[cgen_id] = old_gene
        else:
            new_genome[pos_id] = new_gene
        return(new_genome)
        
    def evaluate(self):
            """
            Creates the input deck, runs the calculation and retrieves the results and the cost.

            Parameters: 
            loc: String - Directory of execution
            fname: String - File name

            Written by Gregory Delipei 7/29/2023
            """

            # Create PARCS INPUT DECK

            pwd = Path(os.getcwd())

            if not os.path.exists(self.name):
                os.makedirs(self.name)
            else:
                shutil.rmtree(self.name, ignore_errors=True)
                os.makedirs(self.name)
            
            cdir = self.library
            shutil.copyfile(cdir + '/' + 'mcyc_exp_quarter.dep', self.name +"/" + 'mcyc_exp.dep')
            os.chdir(self.name)
 
            fuel_locations = list(self.core_dict['fuel']['C1'].keys())
            self.genome_dict = {}
            self.genome_dict['C1']={}
            self.genome_dict['C2']={}
            self.genome_dict['C3']={}
            floc = 0
            for i in range(len(self.genome)):
                if i < 56:
                    ncyc = 1
                    floc = i
                elif i >= 56 and i < 112:
                    ncyc = 2
                    floc = i-56
                else:
                    ncyc = 3
                    floc = i-112
                cyc_tag = 'C' + str(ncyc)
                self.genome_dict[cyc_tag][fuel_locations[floc]]=self.genome[i]
                self.core_dict['fuel'][cyc_tag][fuel_locations[floc]]['Value']=self.genome[i]
                self.core_dict['core'][cyc_tag][fuel_locations[floc]]['Value']=self.genome[i]

            self.full_core = self.get_full_core()
            
            if self.map_size == 'quarter':
                self.core_lattice = self.get_quarter_lattice()
            else:
                self.core_lattice = self.get_full_lattice()

            core_lattice_c1 = copy.deepcopy(self.core_lattice)
            xs_array_c1 = np.zeros((core_lattice_c1.shape[0],core_lattice_c1.shape[1]), dtype='<U20')
            pincal_loc = np.zeros((core_lattice_c1.shape[0],core_lattice_c1.shape[1]))
            for x in range(core_lattice_c1.shape[0]):
                for y in range(core_lattice_c1.shape[1]):
                    loc = core_lattice_c1[x,y]
                    if loc != "00" and loc[0] != "R":
                        core_lattice_c1[x,y] = self.core_dict['Inventory'][self.full_core['C1'][loc]]['Tag']
                        xs_val = self.core_dict['Inventory'][self.full_core['C1'][loc]]['Cross_Section']
                        if xs_val == False:
                            xs_array_c1[x,y] = None
                        else:
                            xs_array_c1[x,y] = xs_val
                            core_lattice_c1[x,y] = '-'+core_lattice_c1[x,y]
                        pincal_loc[x,y]=1
                    elif loc[0] == "R":
                        core_lattice_c1[x,y] = "0   "
                        xs_array_c1[x,y] = None
                        pincal_loc[x,y]=0
                    elif loc == "00":
                        core_lattice_c1[x,y] = "    "
                        xs_array_c1[x,y] = None
                        pincal_loc[x,y]=np.nan

            xs_unique_c1 = np.unique(xs_array_c1)
            xs_unique_c1 = np.delete(xs_unique_c1, np.argwhere(xs_unique_c1 == 'None'))

            core_lattice_c2 = copy.deepcopy(self.core_lattice)
            xs_array_c2 = np.zeros((core_lattice_c2.shape[0],core_lattice_c2.shape[1]), dtype='<U20')
            for x in range(core_lattice_c2.shape[0]):
                for y in range(core_lattice_c2.shape[1]):
                    loc = core_lattice_c2[x,y]
                    if loc != "00" and loc[0] != "R":
                        core_lattice_c2[x,y] = self.core_dict['Inventory'][self.full_core['C2'][loc]]['Tag']
                        xs_val = self.core_dict['Inventory'][self.full_core['C2'][loc]]['Cross_Section']
                        if xs_val == False:
                            xs_array_c2[x,y] = None
                        else:
                            xs_array_c2[x,y] = xs_val
                            core_lattice_c2[x,y] = '-'+core_lattice_c2[x,y]
                            
                    elif loc[0] == "R":
                        core_lattice_c2[x,y] = "0   "
                        xs_array_c2[x,y] = None
                    elif loc == "00":
                        core_lattice_c2[x,y] = "    "
                        xs_array_c2[x,y] = None

            xs_unique_c2 = np.unique(xs_array_c2)
            xs_unique_c2 = np.delete(xs_unique_c2, np.argwhere(xs_unique_c2 == 'None'))

            core_lattice_c3 = copy.deepcopy(self.core_lattice)
            xs_array_c3 = np.zeros((core_lattice_c3.shape[0],core_lattice_c3.shape[1]), dtype='<U20')
            for x in range(core_lattice_c3.shape[0]):
                for y in range(core_lattice_c3.shape[1]):
                    loc = core_lattice_c3[x,y]
                    if loc != "00" and loc[0] != "R":
                        core_lattice_c3[x,y] = self.core_dict['Inventory'][self.full_core['C3'][loc]]['Tag']
                        xs_val = self.core_dict['Inventory'][self.full_core['C3'][loc]]['Cross_Section']
                        if xs_val == False:
                            xs_array_c3[x,y] = None
                        else:
                            xs_array_c3[x,y] = xs_val
                            core_lattice_c3[x,y] = '-'+core_lattice_c3[x,y]
                    elif loc[0] == "R":
                        core_lattice_c3[x,y] = "0   "
                        xs_array_c3[x,y] = None
                    elif loc == "00":
                        core_lattice_c3[x,y] = "    "
                        xs_array_c3[x,y] = None

            xs_unique_c3 = np.unique(xs_array_c3)
            xs_unique_c3 = np.delete(xs_unique_c3, np.argwhere(xs_unique_c3 == 'None'))
            xs_unique = np.append(xs_unique_c1,xs_unique_c2)
            xs_unique = np.append(xs_unique,xs_unique_c3)
            xs_forced = np.array([self.core_dict['Inventory']['FE461']['Cross_Section'],
                        self.core_dict['Inventory']['FE462']['Cross_Section'],
                        self.core_dict['Inventory']['FE501']['Cross_Section'],
                        self.core_dict['Inventory']['FE502']['Cross_Section']])
            xs_unique = np.append(xs_unique,xs_forced)
            xs_unique = np.unique(xs_unique)

            tag_unique = copy.deepcopy(xs_unique)
            xs_ref = np.arange(5,5+len(xs_unique)) # 1-3 for reflectors and 4 for blankets
            for key,value in self.core_dict["Inventory"].items():
                for i in range(xs_unique.shape[0]):
                    if value['Cross_Section']==xs_unique[i]:
                        tag_unique[i]=value['Tag']
            fname = 'solution'
            filename = fname + '.inp'
            with open(filename,"w") as ofile:             
                ofile.write("!******************************************************************************\n")
                ofile.write('CASEID {}  \n'.format(fname))
                ofile.write("!******************************************************************************\n\n")

            with open(filename,"a") as ofile:             
                ofile.write("CNTL\n")
                ofile.write("     RUN_OPTS F T F F\n")
                ofile.write("     TH_FDBK    T\n")
                ofile.write("     INT_TH     T -1\n")
                ofile.write("     CORE_POWER 100.0\n")
                ofile.write("     CORE_TYPE  PWR\n")
                ofile.write("     PPM        1000\n")
                ofile.write("     DEPLETION  T  1.0E-5 T\n")
                ofile.write("     TREE_XS    T  {} T  T  F  F  T  F  T  F  T  F  T  T  T  F \n".format(int(len(xs_unique)+4)))
                ofile.write("     BANK_POS   100 100 100 100 100 100\n")
                ofile.write("     XE_SM      1 1 1 1\n")
                ofile.write("     SEARCH     PPM 1.0 1800.0 10.0\n")
                ofile.write("     MULT_CYC   T\n")
                ofile.write("     XS_EXTRAP  1.0 0.3\n")
                ofile.write("     PIN_POWER  T\n")
                ofile.write("     PLOT_OPTS 0 0 0 0 0 2\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")
                
            with open(filename,"a") as ofile:             
                ofile.write("PARAM\n")
                ofile.write("     LSOLVER  1 1 20\n")
                ofile.write("     NODAL_KERN     NEMMG\n")
                ofile.write("     CMFD     2\n")
                ofile.write("     DECUSP   2\n")
                ofile.write("     INIT_GUESS 0\n")
                ofile.write("     CONV_SS   1.e-6 5.e-5 1.e-3 0.001\n")
                ofile.write("     EPS_ERF   0.010\n")
                ofile.write("     EPS_ANM   0.000001\n")
                ofile.write("     NLUPD_SS  5 5 1\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")
            

            with open(filename,"a") as ofile:             
                ofile.write("GEOM\n")
                ofile.write("     GEO_DIM 9 9 18 1 1\n")
                ofile.write("     RAD_CONF\n")
                ofile.write("     461  461  462  461  502  462  502  462  10\n")   
                ofile.write("     461  462  461  462  461  502  502  462  10\n")
                ofile.write("     461  461  501  461  462  461  501  461  10\n")
                ofile.write("     461  462  461  462  461  501  501  461  10\n")
                ofile.write("     502  461  462  461  462  461  462  10   10\n")
                ofile.write("     462  462  461  462  461  502  461  10   00 \n")
                ofile.write("     502  502  501  501  501  501  10   10   00\n")
                ofile.write("     501  501  461  502  10   10   10   00   00\n")
                ofile.write("     10   10   10   10   10   00   00   00   00\n")
                ofile.write("     GRID_X      1*10.75 8*21.50\n")
                ofile.write("     NEUTMESH_X  1*1 8*1\n")
                ofile.write("     GRID_Y      1*10.75 8*21.50\n")
                ofile.write("     NEUTMESH_Y  1*1 8*1\n")
                ofile.write("     GRID_Z      30.48 15.24 10.16 5.08 10*30.48 5.08 10.16 15.24 30.48\n")            
                ofile.write("     ASSY_TYPE   10   1*2   16*2    1*2 REFL\n")
                for i in range(xs_unique.shape[0]):
                    if 'gd_0' in xs_unique[i]:
                        ofile.write("     ASSY_TYPE   {}   1*1 1*4  14*{}  1*4  1*3 FUEL\n".format(tag_unique[i],xs_ref[i]))
                    else:
                        ofile.write("     ASSY_TYPE   {}   1*1 1*4  1*4 12*{} 1*4 1*4  1*3 FUEL\n".format(tag_unique[i],xs_ref[i]))
                ofile.write("\n")

                ofile.write("     boun_cond   0 2 0 2 2 2\n")
                ofile.write("     SYMMETRY 4\n")

                ofile.write("     PINCAL_LOC\n")
                for x in range(pincal_loc.shape[0]):
                    ofile.write("      ")
                    for y in range(pincal_loc.shape[1]):
                        val = pincal_loc[x,y]
                        if np.isnan(val):
                            pass
                        else:
                            ofile.write(str(int(pincal_loc[x,y])))
                            ofile.write("  ")
                    ofile.write("\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")
            
            with open(filename,"a") as ofile:             
                ofile.write("FDBK\n")
                ofile.write("     FA_POWPIT     {} 21.5\n".format(np.round(self.power/193,4)))
                ofile.write("     GAMMA_FRAC    0.0208    0.0    0.0\n")
                ofile.write("     EFF_DOPLT   T  0.5556\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")


            with open(filename,"a") as ofile:   
                ofile.write("TH\n")          
                ofile.write("     FLU_TYP       0\n")
                ofile.write("     N_PINGT    264 25\n")
                ofile.write("     PIN_DIM      4.1 4.75 0.58 6.13\n")
                ofile.write("     FLOW_COND    {}  {}\n".format(np.round(self.inlet_temperature-273.15,2),np.round(self.flow/193,4)))
                ofile.write("     HGAP     10000.0\n")
                ofile.write("     N_RING   6\n")
                ofile.write("     THMESH_X       9*1\n")
                ofile.write("     THMESH_Y       9*1\n")
                ofile.write("     THMESH_Z       1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18\n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")

            with open(filename,"a") as ofile:             
                ofile.write("DEPL\n")
                ofile.write("     TIME_STP  1 \n")
                ofile.write("     INP_HST   './mcyc_exp.dep' 1 21\n")
                ofile.write("     PMAXS_F   1 '{}' 1\n".format(cdir + '/' + 'xs_gbot'))
                ofile.write("     PMAXS_F   2 '{}' 2\n".format(cdir + '/' + 'xs_grad'))
                ofile.write("     PMAXS_F   3 '{}' 3\n".format(cdir + '/' + 'xs_gtop'))
                ofile.write("     PMAXS_F   4 '{}' 4\n".format(cdir + '/' + 'xs_g250_gd_0_wt_0'))
                for i in range(xs_unique.shape[0]):
                    ofile.write("     PMAXS_F   {} '{}' {}\n".format(5+i,cdir + '/' + xs_unique[i],5+i))
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")

            with open(filename,"a") as ofile:             
                ofile.write("MCYCLE\n")
                ofile.write("  CYCLE_DEF  1\n")
                ofile.write("    DEPL_STEP 0\n")
                ofile.write("    POWER_LEV 2*100.0\n")
                ofile.write("    BANK_SEQ 2*1\n")
                ofile.write("\n")
                ofile.write("  CYCLE_DEF  2\n")
                ofile.write("    DEPL_STEP 1 1 18*30\n")
                ofile.write("    POWER_LEV 21*100.0\n")
                ofile.write("    BANK_SEQ 21*1\n")
                ofile.write("\n")
                ofile.write("  CYCLE_DEF  3\n")
                ofile.write("    DEPL_STEP 1 1 24*30\n")
                ofile.write("    POWER_LEV 27*100.0\n")
                ofile.write("    BANK_SEQ 27*1\n")
                ofile.write("\n")
                ofile.write("  LOCATION\n")
                ofile.write("     H-08  H-09  H-10  H-11  H-12  H-13  H-14  H-15  0\n")   
                ofile.write("     I-08  I-09  I-10  I-11  I-12  I-13  I-14  I-15  0\n")
                ofile.write("     J-08  J-09  J-10  J-11  J-12  J-13  J-14  J-15  0\n")
                ofile.write("     K-08  K-09  K-10  K-11  K-12  K-13  K-14  K-15  0\n")
                ofile.write("     L-08  L-09  L-10  L-11  L-12  L-13  L-14  0     0\n")
                ofile.write("     M-08  M-09  M-10  M-11  M-12  M-13  M-14  0\n")
                ofile.write("     N-08  N-09  N-10  N-11  N-12  N-13  0     0\n")
                ofile.write("     O-08  O-09  O-10  O-11  0     0     0\n")
                ofile.write("     0     0     0     0     0\n")
                ofile.write("\n")

                ofile.write("  SHUF_MAP  1  1\n")
                for x in range(core_lattice_c1.shape[0]):
                    ofile.write("     ")
                    for y in range(core_lattice_c1.shape[1]):
                        ofile.write(core_lattice_c1[x,y])
                        ofile.write("  ")
                    ofile.write("\n")
                ofile.write("\n")

                ofile.write("  SHUF_MAP  2  1\n")
                for x in range(core_lattice_c2.shape[0]):
                    ofile.write("     ")
                    for y in range(core_lattice_c2.shape[1]):
                        ofile.write(core_lattice_c2[x,y])
                        ofile.write("  ")
                    ofile.write("\n")
                ofile.write("\n")

                ofile.write("  SHUF_MAP  3  1\n")
                for x in range(core_lattice_c3.shape[0]):
                    ofile.write("     ")
                    for y in range(core_lattice_c3.shape[1]):
                        ofile.write(core_lattice_c3[x,y])
                        ofile.write("  ")
                    ofile.write("\n")
                ofile.write("\n")

                ofile.write("  CYCLE_IND    1  0  1 \n")
                ofile.write("  CYCLE_IND    2  1  2 \n")
                ofile.write("  CYCLE_IND    3  2  3 \n")
                ofile.write("  CYCLE_IND    4  3  3 \n")
                ofile.write("  CONV_EC      0.1   4 \n")
                ofile.write("\n")
                ofile.write("!******************************************************************************\n\n")
                ofile.write(".")

            # Run PARCS INPUT DECK
            
            parcscmd = "/cm/shared/codes/TRACE51341_PARCS_332/PARCS-v332_Exe/Executables/Linux/parcs-v332-linux2-intel-x64-release.x"
          
            print('Execute PARCS')
            print('Running in process')
            try:
                #
                output = subprocess.check_output([parcscmd, filename], stderr=STDOUT, timeout=240)
                # Get Results
                if 'Finished' in str(output):
                    ofile = fname + '.out'
                    self.get_results(fname,pin_power=False)
                    os.system('rm -f {}.parcs_pin*'.format(fname))
                   # os.system('rm -f {}.inp'.format(fname))
                    os.system('rm -f {}.inp_parcs_err'.format(fname))
                    os.system('rm -f {}.inp_paths_err'.format(fname))
                    os.system('rm -f {}.parcs_cyc-01'.format(fname))
                    os.system('rm -f {}.parcs_cyc-02'.format(fname))
                    os.system('rm -f {}.parcs_cyc-03'.format(fname))
                    os.system('rm -f {}.parcs_cyc-04'.format(fname))
                    os.system('rm -f {}.parcs_dep'.format(fname))
                    os.system('rm -f {}.parcs_itr'.format(fname))
                    os.system('rm -f {}.parcs_msg'.format(fname))
                    os.system('rm -f {}.parcs_out'.format(fname))
                    os.system('rm -f {}.parcs_sum'.format(fname))
                    os.system('rm -f {}.parcs_xml'.format(fname))
                    os.system('rm -f mcyc_exp.dep')
                else:
                    self.parameters["cycle1_length"]['value'] = np.random.uniform(0,10)
                    self.parameters["cycle2_length"]['value'] = np.random.uniform(0,10)
                    self.parameters["cycle3_length"]['value'] = np.random.uniform(0,10)
                    self.parameters["PinPowerPeaking"]['value'] = np.random.uniform(10,20)
                    self.parameters["FDeltaH"]['value'] = np.random.uniform(10,20)
                    self.parameters["max_boron"]['value'] = np.random.uniform(5000,10000)
                    self.parameters["lcoe"]['value'] = np.random.uniform(100,200)  
                    os.system('rm -f ./*')

            except subprocess.TimeoutExpired:
                print('Timed out - killing')
            
                os.system('rm -f {}.parcs_pin*'.format(fname))
                self.parameters["cycle1_length"]['value'] = np.random.uniform(0,10)
                self.parameters["cycle2_length"]['value'] = np.random.uniform(0,10)
                self.parameters["cycle3_length"]['value'] = np.random.uniform(0,10)
                self.parameters["PinPowerPeaking"]['value'] = np.random.uniform(10,20)
                self.parameters["FDeltaH"]['value'] = np.random.uniform(10,20)
                self.parameters["max_boron"]['value'] = np.random.uniform(5000,10000)
                self.parameters["lcoe"]['value'] = np.random.uniform(100,200)
                os.system('rm -f ./*')

            if 'initial' in self.name and self.parameters["max_boron"]['value'] > 5000:
                print('Re-run initial case due to non-convergence')
                self.generate_initial(self.settings['genome']['chromosomes'])
                os.chdir(pwd)
                self.evaluate()
            print('{} calculation is done!'.format(self.name))
            os.chdir(pwd)
            gc.collect()  
            print('finished collecting garbage...')
            print('exiting evaluate...')