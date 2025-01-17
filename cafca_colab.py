# -*- coding: utf-8 -*-
"""CAFCA-Colab.ipynb

# **Colab Initialization**
"""

# from google.colab import drive
from os.path import join
import time
# drive.mount('/gdrive')
# gdrive_root = '/gdrive/My Drive/'

"""# **Interaction Model Abstraction**

Abstract the observable environmental sensing data & communication traces from the logs

## Log Parser
"""
import copy
import os
import numpy as np
from numpy import dot
from numpy.linalg import norm
# import torch

target_scenario = 'COLLISION'  # INPUT: OP_SUCCESS_RATE or COLLISION
LOG_PATH = 'C:/Users/XXXX/IdeaProjects/StarPlateS/SoS_Extension/logs_full'
V_PATH = 'C:/Users/XXXX/IdeaProjects/CAFCA'
IDEAL_PATH = 'C:/Users/XXXX/IdeaProjects/CAFCA/Ideal/Collision'

print('In Log Folder : ', os.listdir(LOG_PATH))

"""## Interaction model generator"""
def IMGenerator():
  IM = [] # A set of all interaction models ======> IM = [im0, im1, im2, im3, ...]
  FIM = [] # A set of failed interaction models
  PIM = [] # A set of passed interaction models
  curnt_id = -1

  f = open(join(V_PATH, target_scenario+'_Verification_Results.csv')) # To check the Verification results
  v_results = f.readlines()
  f.close()

  f = open(join(V_PATH, target_scenario + '_Classification_Results_Test.csv'), encoding='UTF8')  # To get the classification results
  c_results = f.readlines()
  f.close()
  classification_data = []
  for line in c_results:
    line = line.replace(",,","")
    line = line.replace("\n", "")
    classification_data.append(line.split(','))

  im = [] # an interaction model ======> im = [file_id, P/F, Interaction, Env]
  for filename in os.listdir(LOG_PATH):
    if "plnData.txt" not in filename and "vehicleData.txt" not in filename:
      continue
    strings = filename.split('_')
    if int(strings[0]) != curnt_id: # Change to the new failure scenario id
      if len(im) == 4:
        IM.append(copy.deepcopy(im))
        if im[1] == "FALSE":
          FIM.append(copy.deepcopy(im))
        else:
          PIM.append(copy.deepcopy(im))
      im.clear()
      if curnt_id != -1: # Check the progress in console
        print("> Finished\n")
      print("===========" + filename.split('_')[0] + ": Start =======")
      curnt_id = int(strings[0])
      im.append(curnt_id) # Add the file id
      for line in v_results:
        if target_scenario == "COLLISION":
          if str(curnt_id) + '_' in line:
            p_f = line.split(',')[1]
            im.append(p_f)
            break
        else:
          if '\\'+str(curnt_id)+'_' in line.split(',')[0]:  # Add the P/F results of the log file
            p_f = line.split(',')[1]
            im.append(p_f[:len(p_f)-1])
            break
    if 'vehicleData' in strings[1]: # Extract env data
      env = [] # ======> Env = [state0, state1, state2, ...] ordered chronologically
      ret = ""
      f = open(join(LOG_PATH,filename), 'r')
      lines = f.readlines()
      state = [] # A single state (i.e. item) in a log file => [time, veh1, veh1_lane, veh1_loc, veh2, veh2_lane, veh2_loc, ...]
      for i in range(16, len(lines)): # For each line in log file
        line = lines[i]
        line_items = line.split(' ')
        count = 0
        veh_id = -1
        veh_pos = -1
        time_flag = True
        for j in range(1, len(line_items)): # Extract the information by each line
           if line_items[j] != '':
             if count == 0:
               time = line_items[j]
               if float(time) < 20.0:
                 time_flag = False
                 break
               if len(state) == 0:
                 state.append(time)
             elif count == 1:
               veh_id = line_items[j]
               state.append(veh_id)
             elif count == 2:
                state.append(line_items[j])
             elif count == 3:
               veh_pos = line_items[j]
               state.append(veh_pos)
             count += 1
        if not time_flag:
          continue
        if count == 0 and not len(state) == 0:
          env.append(copy.deepcopy(state))
          ret += str(state[0]) + ": "
          for prepro_env in EnvStatePreprocess(state):
            ret += "["
            for prepro_sensor in prepro_env:
              ret += str(prepro_sensor) + ","
            ret += "] "
          ret += "\n"
          state = []
      f.close()
      # f2 = open(join(V_PATH, 'env_state' + str(curnt_id) + '.txt'), 'a')
      # f2.write(ret)
      # f2.close()
      env = np.array(env)
      im.append(copy.deepcopy(env))
    elif 'plnData' in strings[1]: # Extract interaction data
      interaction = [] # ======> interaction = [message0, message1, message2, ...] ordered chronologically
      f = open(join(LOG_PATH,filename), 'r')
      lines = f.readlines()
      F_type = -1
      split_count = -1
      veh_roles = {}
      for i in range(16, len(lines)): # For each line in log file
        message = []
        line = lines[i]
        line = ' '.join(line.split()) # Preprocessing
        line = line.replace(' -', '')
        line_items = line.split(' ')
        if 'MF_Leave' in line: # FollowerLeave type checking for veh role analysis
          split_count = 2
        elif 'EF_Leave' in line:
          split_count = 1
        if len(line_items) > 5: # For each message items => [time, command_sent, sender, sender_role, receiver, receiver_role]
          if float(line_items[0]) < 25.0:
            continue
          time = line_items[0]
          message.append(time)
          command_sent = line_items[4]
          message.append(command_sent)
          if command_sent == 'MERGE_REQ': # Role managmenet code by each role changing CS-level operations
            veh_roles[line_items[1]] = 'Leader'
            if line_items[5] not in veh_roles.keys() or veh_roles[line_items[5]] != 'Left':
              veh_roles[line_items[5]] = 'Leader'
          elif command_sent == 'SPLIT_REQ':
            if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
              veh_roles[line_items[1]] = 'Leader'
          elif command_sent == 'LEAVE_REQ':
            if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
              veh_roles[line_items[1]] = 'Left'
            if line_items[5] not in veh_roles.keys() or veh_roles[line_items[5]] != 'Left':
              veh_roles[line_items[5]] = 'Leader'
          elif command_sent == 'VOTE_LEADER':
            if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
              veh_roles[line_items[1]] = 'Left'
          # elif command_sent == 'ELECTED_LEADER':
          #   if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
          #     veh_roles[line_items[1]] = 'Leader'
          elif command_sent == 'MERGE_DONE':
            if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
              veh_roles.pop(line_items[1])
          elif command_sent == 'SPLIT_DONE':
            split_count -= 1
            if split_count != 0: # Just SPLIT operation && the first SPLIT in MF-LEAVE && LEADER-LEAVE
              if line_items[5] not in veh_roles.keys() or veh_roles[line_items[5]] != 'Left':
                veh_roles[line_items[5]] = 'Leader'
            elif split_count == 0: # The last SPLIT in MF-LEAVE / EF-LEAVE
              if line_items[5] not in veh_roles.keys() or veh_roles[line_items[5]] != 'Left':
                veh_roles[line_items[5]] = 'Left'
          sender = line_items[1]
          message.append(sender)
          if line_items[1] not in veh_roles.keys():
            message.append('Follower')
          else:
            message.append(veh_roles[line_items[1]])
          receiver = line_items[5]
          message.append(receiver)
          if line_items[5] not in veh_roles.keys():
            message.append('Follower')
          else:
            message.append(veh_roles[line_items[5]])
        if len(message) != 0:
          interaction.append(copy.deepcopy(message))
      f.close()
      interaction = np.array(interaction)
      im.append(copy.deepcopy(interaction))
  # print(IM[1865]) # Random print of a single m
  if len(im) == 4:
    IM.append(copy.deepcopy(im))
    if im[1] == "FALSE":
      FIM.append(copy.deepcopy(im))
    else:
      PIM.append(copy.deepcopy(im))
  return IM, FIM, classification_data, PIM

"""## Interaction model txt Writer

"""
def IMtoTxt(IM, fname):
  print("IMtoTxt=== " + fname)
  def ListToString(list_):
    ret = ''
    for sublist_ in list_:
      if ret != '':
        ret = ret[:-1]
        ret += '|'
      for item_ in sublist_:
        ret += str(item_) + ','
    return ret[:-1]

  # File write of IM
  f = open(join(V_PATH,fname), 'w')
  for im in IM:
    f.write(str(im[0]) + '/' + str(im[1]) + '/' + ListToString(im[2]) + '/' + ListToString(im[3]) + '\n')
  f.close()

"""## Interaction model txt reader

"""
def TxttoIM(fname):
  def StringToList(string_):
    ret = []
    sublists = string_.split('|')
    for sublist in sublists:
      sublist = sublist.split(',')
      for id, item in enumerate(sublist): # To remove newline in items
        if '\n' in item:
          sublist[id] = item.rstrip()
      ret.append(copy.deepcopy(sublist))
    return ret

  f = open(join(V_PATH, fname), 'r')
  IM_ = []
  lines = f.readlines()
  for line in lines:
    im_ = line.split('/')
    im_[0] = int(im_[0])
    im_[2] = StringToList(im_[2])
    im_[3] = StringToList(im_[3])
    IM_.append(copy.deepcopy(im_))
  print("FINISH TxttoIM function\n")
  return IM_

"""# **Fuzzy Clustering for Initial Pattern Mining**

Generate initial subsequential patterns by clustering based on the failed logs
Overlapping clustering approach is applied.

## Environmental state & message identity checker
"""
# The function you need to call when you try to check the identity of messages with environmental states.
# Inputs: two messages, the two previously matched messages (None, if not exist), whole Env states for checking the specific points of Env states around the messages, delay_threshold, time_window size for Env state comparison, and env_similarity threshold
def ESMIC(msg_a, msg_b, msg_a_prev, msg_b_prev, env_a, env_b, d_threshold, time_window, env_sim_threshold):
  if not MCT(msg_a, msg_b) or not CalMessageDelay(msg_a, msg_b, msg_a_prev, msg_b_prev, d_threshold):
    return False, None
  env_sim = []
  for state_a in env_a:
    if float(state_a[0]) < float(msg_a[0]) - time_window or float(state_a[0]) > float(msg_a[0]) + time_window:
      continue
    for state_b in env_b:
      if float(state_b[0]) < float(msg_b[0]) - time_window or float(state_b[0]) > float(msg_b[0]) + time_window:
        continue
      # print(state_a[0])
      # print(state_b[0])
      env_sim.append(EnvStateComparePIT(state_a,state_b))
  env_sim = np.array(env_sim)
  # print(env_sim)
  if np.nanmean(env_sim) < env_sim_threshold:
    return False, np.max(env_sim)
  return True, np.max(env_sim)

def MCT(msg_a, msg_b): # Compare the identity of the two messages => [time, command_sent, sender, sender_role, receiver, receiver_role]
  if (msg_a[1] == "ACK" and msg_b[1] == "ACK") or (msg_a[1] == "CHANGE_PL" and msg_b[1] == "CHANGE_PL"):
    return msg_a[1] == msg_b[1] and msg_a[2] == msg_b[2] and msg_a[4] == msg_b[4] and msg_a[3] == msg_b[3] and msg_a[5] == msg_b[5]
  return msg_a[1] == msg_b[1] and msg_a[3] == msg_b[3] and msg_a[5] == msg_b[5]

def CalMessageDelay(msg_a, msg_b, msg_a_prev, msg_b_prev, d_threshold): # Check the delivery intervals of the two messages
  if msg_a_prev is None or msg_b_prev is None:
    return True
  delay_a = float(msg_a[0]) - float(msg_a_prev[0])
  delay_b = float(msg_b[0]) - float(msg_b_prev[0])
  return abs(delay_a - delay_b) <= d_threshold

def EnvStateCompare(state_a, state_b): # Compare the identity of the two Env states => [time, veh1, veh1_lane, veh1_loc, veh2, veh2_lane, veh2_loc, ...]
  veh_a = EnvStatePreprocess(state_a)
  veh_b = EnvStatePreprocess(state_b)
  # print(veh_a)
  # print(veh_b)
  sim_values = []
  for distance_a in veh_a:
    base = np.array(distance_a)
    for distance_b in veh_b:
      if len(base) > len(distance_b):
        base = np.array(distance_b)
        for i in range(0,len(distance_a)-len(base)+1):
          sim_values.append(cos_sim(base, np.array(distance_a[i:i+len(base)])))
      else:
        for i in range(0,len(distance_b)-len(base)+1):
          sim_values.append(cos_sim(base, np.array(distance_b[i:i+len(base)])))
  # print(sim_values)
  return float(np.nanmean(sim_values)) # nanmax -> nanmean

def EnvStateComparePIT(state_a, state_b): # Compare the identity of the two Env states => [time, veh1, veh1_lane, veh1_loc, veh2, veh2_lane, veh2_loc, ...]
  distance_a = np.array(state_a)
  veh_b = EnvStatePreprocess(state_b)
  # print(veh_a)
  # print(veh_b)
  sim_values = []
  for distance_b in veh_b:
    if len(distance_a) > len(distance_b):
      base = np.array(distance_b)
      for i in range(0,len(distance_a)-len(base)+1):
        sim_values.append(cos_sim(base, np.array(distance_a[i:i+len(base)])))
    else:
      base = distance_a
      for i in range(0,len(distance_b)-len(base)+1):
        sim_values.append(cos_sim(base, np.array(distance_b[i:i+len(base)])))
# print(sim_values)
  return float(np.nanmax(sim_values))

def cos_sim(A, B):
  return dot(A, B)/(norm(A)*norm(B))

def EnvStatePreprocess(state): # Initially arrange the Env state data to dictionary & remove unrelated vehicle location data
  dic_state = {}
  ret = []
  for i in range(1,len(state)):
    if i % 3 == 1:
      veh_id = state[i]
    elif i % 3 == 2:
      lane = state[i]
    else:
      dic_state[veh_id] = (lane, state[i])
  if 'veh' in dic_state:
    ret.append(vehDistanceGeneration(dic_state,'veh'))
  if 'veh1' in dic_state:
    ret.append(vehDistanceGeneration(dic_state,'veh1'))
  return ret

def vehDistanceGeneration(dic_state, id):
  veh_location = []
  for key in dic_state.keys():
    lane = dic_state[key][0]
    loc = dic_state[key][1]
    if lane == dic_state[id][0]:
      veh_location.append(float(loc))
  veh_location.sort(reverse=True)
  # print(veh_location)
  veh_distance = []
  for i in range(0, len(veh_location)-1):
    veh_distance.append(Quantification(float(veh_location[i]) - float(veh_location[i+1])))
  return veh_distance

def Quantification(distance): # 5: Very far / 4: Far / 3: Appropriate / 2: Close / 1: Very close
  inter_gap = 105
  intra_gap = 16.5
  if distance > inter_gap: # 262.6 (2.5) -> 84 (0.8)
    return 5
  elif distance > 2.0 * intra_gap: # 33 ~
    return 4
  elif distance > 1.0 * intra_gap: # 20 ~
    return 3
  elif distance > 0.6* intra_gap: # 10 ~
    return 2
  else: # ~ 10
    return 1

#print(ESMIC(IM_[1][2][18], IM_[1][2][18], None, None, IM_[1][3], IM_[1][3], 1.0, 5, 0.8))
# print(IM_[1][3][0])
# print(IM_[1][3][500])
# print(EnvStateCompare(IM_[1][3][0], IM_[1][3][500]))

"""###LCS Algorithm"""
# The function you need to call when you try to calculate the similarity based on the LCS and ESMIC function.
# Inputs: two models (pattern and input), d_threshold
# Outputs: The most critical LCS among possible LCS generation sets, the LCS similarity value with the pattern and input models.
def CAFCASimCal(im_pattern, im_input, d_threshold):
  p = 0.8
  q = 0.2
  generated_pattern, avg_env_sim = GetPatternSim(im_pattern, im_input, d_threshold)
  # generated_pattern, avg_env_sim = GetPatternSimWithoutEnv(im_pattern, im_input, d_threshold)
  # return p * (len(generated_pattern[2]) / (len(im_pattern[2]) * len(im_input[2]))) + q * avg_env_sim
  if generated_pattern[2] is None:
    return 0
  return p * (len(generated_pattern[2]) / len(im_pattern[2])) + q * avg_env_sim

def PatternExtractor(im_pattern, im_input, d_threshold):
  if im_pattern is None or im_input is None or im_pattern[2] is None or im_input[2] is None or im_pattern[3] is None or im_input[3] is None:
    return None
  pattern = im_pattern[2]
  input = im_input[2]
  len_ptn = len(pattern)
  len_input = len(input)
  LCS = np.zeros((len_ptn+1, len_input+1))
  pattern_prev_msg = None
  input_prev_msg = None
  env_sims = []
  input_matched_t = []
  pattern_matched_t = []

  # Generate the LCS table of the interaction models
  for i in range(len_ptn + 1):
    for j in range(len_input + 1):
      if i == 0 or j == 0:
        continue
      if MCT(pattern[i - 1], input[j - 1]) and CalMessageDelay(pattern[i - 1], input[j - 1], pattern_prev_msg, input_prev_msg, d_threshold):
        LCS[i][j] = LCS[i - 1][j - 1] + 1
        pattern_prev_msg = pattern[i - 1]
        input_prev_msg = input[j - 1]
        input_matched_t.append(round(float(pattern[i-1][0]),1))
        pattern_matched_t.append(round(float(input[j-1][0]),1))
      else:
        LCS[i][j] = max(LCS[i][j - 1], LCS[i - 1][j])

  # Extract the LCS from the table
  ret = []
  if LCS[len_ptn][len_input] == 0:
    return None
  else:
    current = 0
    for i in range(1, len_ptn + 1):
      for j in range(1, len_input + 1):
        if LCS[i][j] > current:
          current += 1
          ret.append(pattern[i - 1])

  i = 0
  j = 0
  time_window = 1.0
  input_env = []
  pattern_env = []
  for state_b in im_input[3]:
    if float(state_b[0]) < input_matched_t[j] - time_window:
      continue
    elif float(state_b[0]) > input_matched_t[j]:
      break
    input_env.append(state_b)
    if float(state_b[0]) == input_matched_t[j]:
      for j in range(len(input_matched_t)):
        if input_matched_t[j] < float(input_env[-1][0]):
          continue
        elif input_matched_t[j] > float(input_env[-1][0]):
          break
      if j > len(input_matched_t)-1:
        break

  for state_a in im_pattern[3]:
    if float(state_a[0]) <= pattern_matched_t[i] - time_window:
      continue
    elif float(state_a[0]) > pattern_matched_t[i]:
      break
    pattern_env.append(state_a)
    if float(state_a[0]) == pattern_matched_t[i]:
      for i in range(len(pattern_matched_t)):
        if pattern_matched_t[i] < float(pattern_env[-1][0]):
          continue
        elif pattern_matched_t[i] > float(pattern_env[-1][0]):
          break
      if i > len(pattern_matched_t)-1:
        break

  for (state_a, state_b) in zip(pattern_env, input_env):
    env_sims.append(EnvStateCompare(state_a, state_b))
  #
  # if np.nanmean(env_sims) < 0.8: # env_sim_threshold
  #   env_ret = False
  # env_ret = True
  if env_sims is None or len(env_sims) == 0:
    return ret, pattern_env, 0
  return ret, pattern_env, sum(env_sims) / len(env_sims)

def PatternExtractorWithoutEnv(im_pattern, im_input, d_threshold):
  if im_pattern is None or im_input is None or im_pattern[2] is None or im_input[2] is None:
    return None
  pattern = im_pattern[2]
  input = im_input[2]
  len_ptn = len(pattern)
  len_input = len(input)
  # LCS = [[0] * (len_input + 1) for i in range(len_ptn + 1)]
  LCS = np.zeros((len_ptn+1, len_input+1))
  pattern_prev_msg = None
  input_prev_msg = None

  # Generate the LCS table of the interaction models
  for i in range(len_ptn + 1):
    for j in range(len_input + 1):
      if i == 0 or j == 0:
        continue
      if MCT(pattern[i-1], input[j-1]) and CalMessageDelay(pattern[i - 1], input[j - 1], pattern_prev_msg, input_prev_msg, d_threshold):  # Env State & Message Identity Checking (ESMIC) function usage example.
        LCS[i][j] = LCS[i - 1][j - 1] + 1 # Save the env_sim values when the two messages are matched.
        # You need to check the previously matched messages for checking the message delivery intervals of the two messages, respectively
        pattern_prev_msg = pattern[i - 1]
        input_prev_msg = input[j - 1]
      else:
        LCS[i][j] = max(LCS[i][j - 1], LCS[i - 1][j])

  # Extract the LCS from the table
  ret = []
  if LCS[len_ptn][len_input] == 0:
    return None
  else:
    current = 0
    for i in range(1, len_ptn + 1):
      for j in range(1, len_input + 1):
        if LCS[i][j] > current:
          current += 1
          ret.append(pattern[i - 1])  # TODO should be modified by model
    return ret

def GetPattern(im_pattern, im_input, d_threshold, min_len_threshold):  # LCS pattern extraction function
  if im_pattern is None:
    return im_input
  generated_lcs = []
  generated_avg_env_sim = []
  generated_env = []
  ret = []  # returned pattern with the structure of im.
  T = [25, 45, 65, 85]
  for t in T:
    for t_ in T:
      generated_pattern, sliced_env, avg_env_sim = PatternExtractor(InteractionSeqSlicer(im_pattern, t),InteractionSeqSlicer(im_input, t_),d_threshold) or (None, None, None)
      generated_lcs.append(generated_pattern)
      generated_env.append(sliced_env)
      generated_avg_env_sim.append(avg_env_sim)
      if generated_pattern is None: # Don't need to check the other consecutive options if a None appears
        break
  max_LCS, max_env = GetMaxContentLCS(generated_lcs, generated_env)
  if max_LCS is None or len(max_LCS) < min_len_threshold or max_env is None:
    max_LCS = im_pattern[2]
    max_env = im_pattern[3]
  ret.append(im_pattern[0])
  ret.append(im_pattern[1])
  ret.append(max_LCS)
  ret.append(max_env)
  return ret

def GetPatternSim(im_pattern, im_input, d_threshold):  # LCS pattern extraction function
  if im_pattern is None:
    return im_input
  generated_lcs = []
  generated_avg_env_sim = []
  generated_env = []
  ret = []  # returned pattern with the structure of im.
  T = [25, 45, 65, 85]
  for t in T:
    for t_ in T:
      generated_pattern, sliced_env, avg_env_sim = PatternExtractor(InteractionSeqSlicer(im_pattern, t), InteractionSeqSlicer(im_input, t_), d_threshold) or (None, None, 0)
      generated_lcs.append(generated_pattern)
      generated_env.append(sliced_env)
      generated_avg_env_sim.append(avg_env_sim)
      if generated_pattern is None: # Don't need to check the other consecutive options if a None appears
        break
  max_LCS, max_env = GetMaxContentLCS(generated_lcs, generated_env)
  ret.append(im_pattern[0])
  ret.append(im_pattern[1])
  ret.append(max_LCS)
  ret.append(max_env)
  return ret, np.nanmax(generated_avg_env_sim)

def GetPatternWithoutEnv(im_pattern, im_input, d_threshold, min_len_threshold):
  if im_pattern is None:
    return im_input
  generated_lcs = []
  ret = []  # returned pattern with the structure of im.
  T = [25, 45, 65, 85]
  # for t in T:
    # generated_pattern = PatternExtractorWithoutEnv(InteractionSeqSlicer(im_pattern, t),
    #                                                InteractionSeqSlicer(im_input, t), d_threshold)
    # generated_lcs.append(generated_pattern)
  for t in T:
    for t_ in T:
      # generated_pattern, avg_env_sim = PatternExtractor(InteractionSeqSlicer(im_pattern, t), InteractionSeqSlicer(im_input, t), d_threshold)
      generated_pattern = PatternExtractorWithoutEnv(InteractionSeqSlicer(im_pattern, t),
                                                     InteractionSeqSlicer(im_input, t_), d_threshold)
      generated_lcs.append(generated_pattern)
      if generated_pattern is None: # Don't need to check the other consecutive options if a None appears
        break
  max_LCS, max_avg_env_sim = GetMaxContentLCS(generated_lcs, None)
  if not max_LCS or len(max_LCS) < min_len_threshold:
    max_LCS = im_pattern[2]
  ret.append(im_pattern[0])
  ret.append(im_pattern[1])
  ret.append(max_LCS)
  ret.append([])
  return ret

def GetPatternSimWithoutEnv(im_pattern, im_input, d_threshold):
  if im_pattern is None:
    return im_input
  generated_lcs = []
  ret = [] # returned pattern with the structure of im.
  T = [25, 45, 65, 85]
  for t in T:
    # generated_pattern= PatternExtractorWithoutEnv(im_pattern, InteractionSeqSlicer(im_input, t), d_threshold)
    # generated_lcs.append(generated_pattern)
    for t_ in T:
      # generated_pattern, avg_env_sim = PatternExtractor(InteractionSeqSlicer(im_pattern, t), InteractionSeqSlicer(im_input, t), d_threshold)
      generated_pattern= PatternExtractorWithoutEnv(InteractionSeqSlicer(im_pattern, t),InteractionSeqSlicer(im_input, t_), d_threshold)
      generated_lcs.append(generated_pattern)
      if generated_pattern is None: # Don't need to check the other consecutive options if a None appears
        break
  max_LCS, max_avg_env_sim = GetMaxContentLCS(generated_lcs, None)
  ret.append(im_pattern[0])
  ret.append(im_pattern[1])
  ret.append(max_LCS)
  ret.append([])
  return ret, 0

def GetMaxContentLCS(generated_lcs, generated_env):  # GetMaxContentLCS among the generated LCSs
  ret_max = None
  ret_max_env = None
  max_contents = -1
  max_len = -1
  if not generated_lcs:
    return None, None
  if not generated_env is None:
    for idx, lcs_pattern in enumerate(generated_lcs):
      if not lcs_pattern:
        continue
      contents = set()
      for message in lcs_pattern:
        contents.add(message[1])
      if len(contents) > max_contents:  # Compare the number of types of contents in LCS pattern
        max_contents = len(contents)
        ret_max = lcs_pattern
        ret_max_env = generated_env[idx]
        max_len = len(lcs_pattern)
      elif len(contents) == max_contents:  # If the number of content-types are same, select the shorter one.
        if max_len < len(lcs_pattern):
          max_contents = len(contents)
          ret_max = lcs_pattern
          ret_max_env = generated_env[idx]
          max_len = len(lcs_pattern)
    return ret_max, ret_max_env
  else:
    for idx, lcs_pattern in enumerate(generated_lcs):
      if not lcs_pattern:
        continue
      contents = set()
      for message in lcs_pattern:
        contents.add(message[1])
      if len(contents) > max_contents:  # Compare the number of types of contents in LCS pattern
        max_contents = len(contents)
        ret_max = lcs_pattern
        max_len = len(lcs_pattern)
      elif len(contents) == max_contents:  # If the number of content-types are same, select the shorter one.
        if max_len < len(lcs_pattern):
          max_contents = len(contents)
          ret_max = lcs_pattern
          max_len = len(lcs_pattern)
    return ret_max, None

def InteractionSeqSlicer(im,time):  # Only slice the message sequences by the time TODO: If necessary, cover Env slicing too?
  if time == 25:
    return im
  if im is None or im[2] is None or im[3] is None:
    return im
  ret = copy.deepcopy(im)
  ret_interaction = None
  for idx, message in enumerate(im[2]):
    if float(message[0]) >= time:
      ret_interaction = im[2][idx:]
      break
  ret[2] = ret_interaction
  return ret

def MTSPattern(im_pattern, im_input, p, q, min_len_threshold):
  TIME_WINDOW_SIZE = 20.0
  max_tw = None
  max_sim = -1
  if im_pattern is None:
    return im_input
  for s_time_pattern in range(25, 80, 5):
    for s_time_input in range(25, 80, 5):
      pattern_tw = InteractionTWSlicer(im_pattern, float(s_time_pattern), float(s_time_pattern) + TIME_WINDOW_SIZE)
      input_tw = InteractionTWSlicer(im_input, float(s_time_input), float(s_time_input) + TIME_WINDOW_SIZE)
      if pattern_tw is None or input_tw is None or pattern_tw[2] is None or input_tw[2] is None:
        continue
      mts_sim = MTSSim(pattern_tw, input_tw, p,q)
      if mts_sim > max_sim:
        max_tw = copy.deepcopy(pattern_tw)
        max_sim = mts_sim
  if max_tw is None or len(max_tw) < min_len_threshold:
    max_tw = im_pattern
  return max_tw

def MTS(im_pattern, im_input, p, q):
  TIME_WINDOW_SIZE = 20.0
  max_tw = None
  max_sim = -1
  for s_time_pattern in range(25, 80, 5):
    for s_time_input in range(25, 80, 5):
      pattern_tw = InteractionTWSlicer(im_pattern, float(s_time_pattern), float(s_time_pattern) + TIME_WINDOW_SIZE)
      input_tw = InteractionTWSlicer(im_input, float(s_time_input), float(s_time_input) + TIME_WINDOW_SIZE)
      if pattern_tw is None or input_tw is None or pattern_tw[2] is None or input_tw[2] is None:
        continue
      mts_sim = MTSSim(pattern_tw, input_tw, p,q)
      if mts_sim > max_sim:
        max_tw = copy.deepcopy(pattern_tw)
        max_sim = mts_sim

  return max_sim

def MTSSim(im_pattern_tw, im_input_tw, p, q):
  # Message identity counting
  # pattern_prev_msg = None
  # input_prev_msg = None
  message_identity_count = 0
  input_matched_t = []
  pattern_matched_t = []

  if im_pattern_tw is None or im_pattern_tw[2] is None or im_input_tw is None or im_input_tw[2] is None or im_input_tw[3] is None or im_pattern_tw[3] is None:
    return 0

  for (message_p, message_i) in zip(im_pattern_tw[2], im_input_tw[2]):
    if MCT(message_p, message_i):
      message_identity_count += 1
      input_matched_t.append(round(float(message_p[0]), 1))
      pattern_matched_t.append(round(float(message_i[0]), 1))

  if message_identity_count == 0 or len(input_matched_t) == 0 or len(pattern_matched_t) == 0:
    return 0
  time_window = 1.0
  i = 0
  j = 0
  input_env = []
  pattern_env = []
  env_sims = []
  for state_b in im_input_tw[3]:
    if float(state_b[0]) < input_matched_t[j] - time_window:
      continue
    elif float(state_b[0]) > input_matched_t[j]:
      break
    input_env.append(state_b)
    if float(state_b[0]) == input_matched_t[j]:
      for j in range(len(input_matched_t)):
        if input_matched_t[j] < float(input_env[-1][0]):
          continue
        elif input_matched_t[j] > float(input_env[-1][0]):
          break
      if j > len(input_matched_t) - 1:
        break

  for state_a in im_pattern_tw[3]:
    if float(state_a[0]) <= pattern_matched_t[i] - time_window:
      continue
    elif float(state_a[0]) > pattern_matched_t[i]:
      break
    pattern_env.append(state_a)
    if float(state_a[0]) == pattern_matched_t[i]:
      for i in range(len(pattern_matched_t)):
        if pattern_matched_t[i] < float(pattern_env[-1][0]):
          continue
        elif pattern_matched_t[i] > float(pattern_env[-1][0]):
          break
      if i > len(pattern_matched_t) - 1:
        break

  for (state_a, state_b) in zip(pattern_env, input_env):
    env_sims.append(EnvStateCompare(state_a, state_b))

  return (message_identity_count / len(im_pattern_tw[2])) * p + (sum(env_sims) / len(env_sims)) * q

def InteractionTWSlicer(im, s_time, e_time):
  if im is None or im[2] is None:
    return im
  ret = copy.deepcopy(im)
  ret_interaction = []
  for message in im[2]:
    if float(message[0]) > e_time:
      break
    if float(message[0]) >= s_time:
      ret_interaction.append(message)
  ret_interaction = np.array(ret_interaction)
  ret[2] = ret_interaction
  return ret

"""### SPADE Pattern Mining

"""

def SequenceDBBuilder(IMs):
  # IMs(interaction models) - 0: seqid, 1: P/F, 2: messages, 3: environmental states
  seqDB = set() # set of events (seqid, time(eventid), command-sender-receiver-delay)

  for m in IMs:
    for i in range(len(m[2])):
      msg_t = float(m[2][i][0]) # obtain message time
      if msg_t < 25.00: # only consider the messages after 25.00 sec
        continue
      msg = m[2][i];
      # delay categorization
      prev_msg = m[2][i-1] if (i-1)>=0 else m[2][0]
      delay = int(msg_t - float(prev_msg[0]))
      # message is categorized using command, sender role, receiver role, and delay
      event = (m[0], msg_t, (msg[1]+"-"+msg[3]+"-"+msg[5]+"-"+str(delay)))
      seqDB.add(event)
  return seqDB

def VerticalIdListBuilder(seqDB):
  vIdList = {} # key: message type (element), value: list of (seqid, time)
  for e in seqDB:
    ids = e[0:2]
    if e[2] not in vIdList:
      vIdList[e[2]]=[]
    vIdList[e[2]].append(ids)
  return vIdList

def FrequentElementExtractor(vIdList, sup_threshold): # filter out sequence atoms based on the support threshold
  frequentEleSet = {} # key: sequence atom, value: list of (seqid, time)
  for key, value in vIdList.items():
    s=set()
    for v in value: # count how many sequences has the sequence atom
      s.add(v[0])
    if len(s) >= sup_threshold:
      frequentEleSet[key] = value
  return frequentEleSet

def TemporalJoin(element_a, element_b): # temporal join two sequence atoms' id lists
  resultList = {} # key: new sequence atom (combining element_a & element_b), value: list of (seqid, time)

  for event_a in element_a[1]:
    for event_b in element_b[1]:
      if event_a[0] == event_b[0]: # seqid
        if event_a[1] < event_b[1]: # time
          newSeq = tuple(element_a[0]+[element_b[0][-1]])
          if newSeq not in resultList: 
            resultList[newSeq] = set()
          resultList[newSeq].add(event_b)
        elif event_a[1] > event_b[1]: # time
          newSeq = tuple(element_b[0]+[element_a[0][-1]])
          if newSeq not in resultList: 
            resultList[newSeq] = set()
          resultList[newSeq].add(event_a)
        elif element_a[0][-1] != element_b[0][-1]:
          newSeq_1 = tuple(element_a[0][:-1] + sorted([element_a[0][-1],element_b[0][-1]]))
          if newSeq_1 not in resultList: 
            resultList[newSeq_1] = set()
          resultList[newSeq_1].add(event_b)
          newSeq_2 = tuple(element_b[0][:-1] + sorted([element_a[0][-1],element_b[0][-1]]))
          if newSeq_1 != newSeq_2: 
            if newSeq_2 not in resultList: 
              resultList[newSeq_2] = set()
            resultList[newSeq_2].add(event_b)
  return resultList

def Frequent2ElementSequenceExtractor(freqEleList, sup_threshold): # extract all the frequent 2-sequences
  # build a horizontal database from vertical id list of elements
  horizontalDB = {} # key: seqid, value: list of (element, time)
  for e, idlist in freqEleList.items():
    for ids in idlist:
      if ids[0] not in horizontalDB:
        horizontalDB[ids[0]] = []
      horizontalDB[ids[0]].append([e, ids[1]])

  # construct all the 2-sequence in the database, and count the number of 2-sequence
  count2EleSeq = {} # key: 2-sequence, value: number of the 2-sequence
  for sid, sequence in horizontalDB.items():
    for index_a, event_a in enumerate(sequence):
      for index_b, event_b in enumerate(sequence[index_a+1:]):
        # compare the time of two events, and construct 2-sequence
        if event_a[1] <= event_b[1]:
          twoEleSeq = (event_a[0], event_b[0])
        else: 
          twoEleSeq = (event_b[0], event_a[0])
        # count the number of 2-sequence
        if twoEleSeq not in count2EleSeq:
          count2EleSeq[twoEleSeq] = 0
        count2EleSeq[twoEleSeq] += 1

  # based on elements of 2-sequence, temporal join two id lists to get the 2-sequence's id lists
  newSeqEleIdList = {} # key: 2-sequence, value: set of (seqid, time)
  for twoSeq, count in count2EleSeq.items():
    if count < sup_threshold:
      continue
    if twoSeq[0] == twoSeq[1]: 
      continue
    joinedIdList = TemporalJoin([[twoSeq[0]], freqEleList[twoSeq[0]]], [[twoSeq[1]], freqEleList[twoSeq[1]]])
    for seq, idlist in joinedIdList.items():
      if seq not in newSeqEleIdList:
        newSeqEleIdList[seq] = set()
      newSeqEleIdList[seq].update(idlist)
  
  return FrequentElementExtractor(newSeqEleIdList, sup_threshold)

def EnumerateFrequentSequence(freqEleList, freqSeqEle, sup_threshold): # find the remaining sequence atoms (3-sequences, 4-sequences, ...)
  # temporal join each two sequence atoms to construct new sequence atoms
  newSeqEleIdList = {}
  for index_a, seq_a in enumerate(freqEleList.keys()):
    for index_b, seq_b in enumerate(list(freqEleList.keys())[index_a+1:]):
      joinedIdList = TemporalJoin([list(seq_a), freqEleList[seq_a]], [list(seq_b), freqEleList[seq_b]])
      for seq, idlist in joinedIdList.items():
        if seq not in newSeqEleIdList:
          newSeqEleIdList[seq] = set()
        newSeqEleIdList[seq].update(idlist)
  newSeqEleIdList = FrequentElementExtractor(newSeqEleIdList, sup_threshold)

  # store new frequent sequences in freqSeqEle
  for s, idlist in newSeqEleIdList.items():
    if s not in freqSeqEle:
      freqSeqEle[s] = set()
    freqSeqEle[s].update(idlist)
    
  # Breadth-first-search to contruct new sequence atoms
  if newSeqEleIdList:
    EnumerateFrequentSequence(newSeqEleIdList, freqSeqEle, sup_threshold)

  return freqSeqEle

def SPADE_PatternMining(IMs, sup_threshold):
  print("START Sequence DB BUILDER\n")
  sequences = SequenceDBBuilder(IMs)
  print("START VerticalIDListBuilder\n")
  singleIdList = VerticalIdListBuilder(sequences)
  print("START FrequentElementExtractor\n")
  frequentMsgList = FrequentElementExtractor(singleIdList, sup_threshold)
  print("START FrequentElement2SequenceExtractor\n")
  frequent2MsgSeqList = Frequent2ElementSequenceExtractor(frequentMsgList, sup_threshold)
  freqSeqEle = {} # key: sequence atoms (3-sequence, 4-sequence,...), value: set of (seqid, time)
  print("START EnumFrequentSequence\n")
  frequentMsgSeqList = EnumerateFrequentSequence(frequent2MsgSeqList, freqSeqEle, sup_threshold)
  # frequentMsgSeqList.update(frequent2MsgSeqList)
  # frequentMsgSeqList.update(frequentMsgList)

  # Frequency-based sorting
  frequency = {}
  for seq, idlist in frequentMsgSeqList.items():
    s=set()
    for id in idlist:
      s.add(id[0])
    frequency[seq] = len(s)
  sortedFrequency = sorted(frequency.items(), key=lambda x: x[1], reverse=True)
  sortedFrequentSeqList = []
  for f in sortedFrequency:
    sortedFrequentSeqList.append((f[0], f[1], frequentMsgSeqList[f[0]]))

  return sortedFrequentSeqList

def SPADEListtoString(item_list):
  ret = ''
  for item_ in item_list:
    ret += item_ + "/"
  return ret[:-1]

def SPADESettoString(item_set):
  ret = ''
  for item_tuple in item_set:
    for item_ in item_tuple:
      ret += str(item_) + ":"
    ret = ret [:-1]
    ret += "/"
  return ret[:-1]

def RunSPADE(IM):
  s_threshold = len(IM)*0.75
  for i in range(21, 31):
    random.seed(i)
    random.shuffle(IM)
    print(IM[0])
    frequentSequenceSet = SPADE_PatternMining(IM, s_threshold)
    print(frequentSequenceSet)
    print(len(frequentSequenceSet))

    f = open(join(V_PATH, 'SPADE_11_0.78.txt'), 'w')
    for item in frequentSequenceSet:
      f.write(SPADEListtoString(item[0]) + '\n' + SPADESettoString(list(item[2])) + '\n')
    f.close()

  # del frequentSequenceSet
  # gc.collect()

"""### LOGLINER & LOGFAULTFLAGGER"""

import math

def LogAbstractor(IMs):
  # IMs(interaction models) - 0: seqid, 1: P/F, 2: messages, 3: environmental states
  logs = [] # list of logs [logid, [line1, line2, line3, ...]]   line: command-sender-receiver

  for m in IMs:
    lines = set()
    if m[1] == "FALSE":
      for i in range(len(m[2])):
        msg_t = float(m[2][i][0]) # obtain message time
        if msg_t < 25.00: # only consider the messages after 25.00 sec
          continue
        msg = m[2][i];
        # log is abstracted to command-sender_role-receiver_role
        line = msg[1]+"-"+msg[3]+"-"+msg[5]
        lines.add(line)
      logs.append([m[0], lines])
  return logs

def LogLineIDFBuilder(logs, corpus): # build a corpus that contains unique log lines and calculate the idf for each logline
  logLineCount = {} # key: logline, value: number of logs that contain the logline
  # count the frequency of each log line in the whole log files
  for log in logs:
    for line in log[1]:
      if line not in corpus:
        corpus.append(line)
        logLineCount[line] = 0
      logLineCount[line]+=1
  # calculate line-IDF
  numberOfLogs = len(logs)
  lineIDF = {} # key: logline, value: line-IDF
  for key, value in logLineCount.items():
    lineIDF[key] = math.log(numberOfLogs / value)
  return lineIDF

def LogLineFlagger(logs, lineIDF, N): # find the N rarest log lines in each log file
  logLineIDF = [] # list of logs with their flagged log lines [logid, [(line1, idf), ..., (lineN, idf)]]

  for log in logs:
    IDFList = []
    for line in log[1]:
      IDFList.append((line, lineIDF[line]))
    # sort loglines by line-idf
    IDFList.sort(key = lambda x: x[1], reverse=True)
    if len(IDFList) <= N:
      logLineIDF.append([log[0], IDFList])
    else:
      logLineIDF.append([log[0], IDFList[0:N]])
  return logLineIDF

def Vectorization(logLineIDF, corpus):
  logVector = [] # list of logs with their vector [logid, vector], vector dimension is length of corpus (number of unique log lines)
  for log in logLineIDF:
    v = [0] * len(corpus)
    for line in log[1]:
      v[corpus.index(line[0])] = line[1]
    logVector.append([log[0], v])
  return logVector

def LogLiner(IMs, N):
  corpus = []
  logs = LogAbstractor(IMs)
  lineIDF = LogLineIDFBuilder(logs, corpus)
  # flaggedLines = LogLineFlagger(logs, lineIDF, N)
  # logVecotrs = Vectorization(flaggedLines, corpus)
  # return flaggedLines, logVecotrs
  return lineIDF

def RunLogLiner(IM, classification_data):
  for i in range(0, 30):
    random.shuffle(IM)
    print(IM[0])

    for j in range(0, 12):
      IM_batch = []
      print(classification_data[j])
      for im in IM:
        if str(im[0])+'_0' in classification_data[j]:
          IM_batch.append(im)
      print(IM_batch)
      # flaggedLines, logVecotrs = LogLiner(IM, 5)
      lineIDF = LogLiner(IM_batch, 5)
      print(lineIDF)

      f = open(join(V_PATH, 'LogLiner_' + str(i) + '_' + str(j) + '.csv'), 'w')
      for key, val in lineIDF.items():
        f.write(str(key) + ',' + str(val) + '\n')
      f.close()

"""####Processing ideal examples of fault class"""
def FaultClassProcess():
  class_PATH = join(V_PATH, 'Ideal/')
  classLogs = []
  for filename in os.listdir(class_PATH):
    strings = filename.split('_')
    if 'plnData_class' in filename:
      classFile = open(join(class_PATH,filename), 'r')
      lines = classFile.readlines()
      split_count = -1
      veh_roles = {}
      iteraction = []
      for i in range(4, len(lines)):
        message = []
        line = lines[i]
        line = ' '.join(line.split()) # Preprocessing
        line = line.replace(' -', '')
        line_items = line.split(' ')
        if 'MF_Leave' in line: # FollowerLeave type checking for veh role analysis
          split_count = 2
        elif 'EF_Leave' in line:
          split_count = 1
        if len(line_items) > 5: # For each message items => [time, command_sent, sender, sender_role, receiver, receiver_role]
          time = line_items[0]
          message.append(time)
          command_sent = line_items[4]
          message.append(command_sent)
          if command_sent == 'MERGE_REQ': # Role managmenet code by each role changing CS-level operations
            veh_roles[line_items[1]] = 'Leader'
            if line_items[5] not in veh_roles.keys() or veh_roles[line_items[5]] != 'Left':
              veh_roles[line_items[5]] = 'Leader'
          elif command_sent == 'SPLIT_REQ':
            if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
              veh_roles[line_items[1]] = 'Leader'
          elif command_sent == 'LEAVE_REQ':
            if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
              veh_roles[line_items[1]] = 'Left'
            if line_items[5] not in veh_roles.keys() or veh_roles[line_items[5]] != 'Left':
              veh_roles[line_items[5]] = 'Leader'
          elif command_sent == 'VOTE_LEADER':
            if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
              veh_roles[line_items[1]] = 'Left'
          elif command_sent == 'MERGE_DONE':
            if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
              veh_roles.pop(line_items[1])
          elif command_sent == 'SPLIT_DONE':
            split_count -= 1
            if split_count != 0: # Just SPLIT operation && the first SPLIT in MF-LEAVE && LEADER-LEAVE
              if line_items[5] not in veh_roles.keys() or veh_roles[line_items[5]] != 'Left':
                veh_roles[line_items[5]] = 'Leader'
            elif split_count == 0: # The last SPLIT in MF-LEAVE / EF-LEAVE
              if line_items[5] not in veh_roles.keys() or veh_roles[line_items[5]] != 'Left':
                veh_roles[line_items[5]] = 'Left'
          sender = line_items[1]
          message.append(sender)
          if line_items[1] not in veh_roles.keys():
            message.append('Follower')
          else:
            message.append(veh_roles[line_items[1]])
          receiver = line_items[5]
          message.append(receiver)
          if line_items[5] not in veh_roles.keys():
            message.append('Follower')
          else:
            message.append(veh_roles[line_items[5]])
          # interaction.append(message) // TODO
      classFile.close()
        # classLogs.append([int(strings[0]), 'FALSE', interaction]) // TODO

def LogFaultFlagger(IMs, faultClassLogs, N):
  corpus = []
  logs = LogAbstractor(IMs)
  processedClassLogs = LogAbstractor(faultClassLogs)

  lineIDF = LogLineIDFBuilder(logs, corpus)
  # calculate fault count
  faultCount = {}
  for log in processedClassLogs:
    for line in log[1]:
      if line not in faultCount:
        faultCount[line] = 0
      faultCount[line]+=1
  # update IDF with fault count
  for key in faultCount.keys():
    lineIDF[key]*=(1+faultCount[key])

  flaggedLines = LogLineFlagger(logs, lineIDF, N)
  logVecotrs = Vectorization(flaggedLines, corpus)
  return flaggedLines, logVecotrs

def RunLogFaultFlagger(IM, classLogs):
  flaggedLines, logVecotrs = LogFaultFlagger(IM, classLogs, 5)
  print(flaggedLines)

"""## Fuzzy Clustering"""

import random
import math

def FCM(cl_type, IM_, DELAY_THRESHOLD, SIM_THRESHOLD, MIN_LEN_THRESHOLD, C_VALUE, ideal_patterns, oracle_batch, IM_Index, PIM_Batch): # TODO cl_type: FCM, PFS (Picture Fuzzy Set), KS2M
  INIT_SIM_THRESHOLD = 0.3
  MAX_INIT_SIM_THRESHOLD = 0.5
  SENSITIVITY_THRESHOLD = 0.005
  MAX_ITERATION = 20
  m = 2 # Fuzzy value

  simvalues = np.zeros((len(IM_),C_VALUE))
  simvalues_item = np.zeros((len(IM_), len(IM_)))
  memberships = np.zeros((len(IM_),C_VALUE))
  prev_memberships = np.random.rand(len(IM_), C_VALUE)
  iterations = 0
  start_time = time.time()
  if cl_type == 1 or cl_type == 2: # 0: FCM 1: CAFCA 2: KS2M
    print("============== Item Comparison ==============")
    for k in range(len(IM_)):
      print("Run for " + str(k) + "th iteration")
      for l in range(len(IM_)):
        if k == l:
          simvalues_item[k][l] = 1.0
        elif k < l:
          simvalues_item[k][l] = CAFCASimCal(IM_[k], IM_[l], DELAY_THRESHOLD)
    diss_item = 1 - simvalues_item
  if target_scenario == "COLL":
    k = 4
  else:
    k = 12
  # k_largest_index = np.column_stack(np.unravel_index(np.argpartition(diss_item.ravel(),diss_item.size-k)[-k:], diss_item.shape))
  print("============== FCM Run ==============")
  patterns = []
  index = np.random.choice(IM_.shape[0], C_VALUE, replace=False)
  for id in index:
    patterns.append(IM_[id])
  patterns = np.array(patterns)
  # while True: # Initial selection of C models from the whole models
  #   initial_sims = []
  #   max_flag = True
  #   patterns = []
  #   # while len(patterns) < C_VALUE: # Select C numbers of models
  #   #   item = IM_[random.randint(0,len(IM_)-1)]
  #   #   if (item not in patterns).any():
  #   #     patterns.append(item)
  #   if cl_type == 0:
  #     index = np.random.choice(IM_.shape[0], C_VALUE, replace=False)
  #     for id in index:
  #       patterns.append(IM_[id])
  #     patterns = np.array(patterns)
  #     for i in range(0, len(patterns)-1):
  #       for j in range(i+1, len(patterns)):
  #         init_sim_value = CAFCASimCal(patterns[i], patterns[j], DELAY_THRESHOLD) # Calculate the LCS_Sim values for each combination of initally selected models
  #         if init_sim_value > MAX_INIT_SIM_THRESHOLD: # If two of them are highly simialr, choose the other models
  #           max_flag = False
  #           break
  #         initial_sims.append(init_sim_value)
  #       if not max_flag:
  #         initial_sims.clear()
  #         break
  #     if max_flag and len(initial_sims) > 0 and sum(initial_sims)/len(initial_sims) < INIT_SIM_THRESHOLD: # If the average of the LCS_sim values of the models is non-acceptable, find other set of models
  #       break
  #   elif cl_type == 1 or cl_type == 2:
  #     # index = np.unique(k_largest_index.ravel())[:C_VALUE]
  #     print(diss_item)
  #     index = np.random.choice(IM_.shape[0], C_VALUE, replace=False)
  #     for id in index:
  #       patterns.append(IM_[id])
  #     patterns = np.array(patterns)
  #     break
      # print(k_largest_index)
      # np.sort(index)
      # for id in index:
      #   patterns.append(IM_[id])
      # patterns = np.array(patterns)
      # for i in range(0, len(patterns)-1):
      #   for j in range(i+1, len(patterns)):
      #     if simvalues_item[index[i]][index[j]] > MAX_INIT_SIM_THRESHOLD: # If two of them are highly simialr, choose the other models
      #       max_flag = False
      #       break
      #     initial_sims.append(simvalues_item[index[i]][index[j]])
      #   if not max_flag:
      #     initial_sims.clear()
      #     break
      # if max_flag and len(initial_sims) > 0: #and sum(initial_sims)/len(initial_sims) < INIT_SIM_THRESHOLD: # If the average of the LCS_sim values of the models is non-acceptable, find other set of models
      #   break

  print("============== Initial Patterns Selected ==============")
  prev_objs = -1 # Sum of Squared Errors for Fuzzy C-means clustering
  f = open(join(V_PATH, "COLL_CAFCA_DPM_p_8_q_2.csv"), 'a')
  while iterations < MAX_ITERATION:
    print("============== Iterations: " + str(iterations))
    start_time = time.time()
    # If Patterns have None object, replace it to random im.
    for i in range(len(patterns)):
      if patterns[i] is None:
        patterns[i] = IM_[random.randint(0,len(IM_)-1)]

    # Similarity & Dissimilarity value calculation between patterns and models
    if (cl_type == 1 or cl_type == 2) and iterations == 0:
      for k in range(len(IM_)):
        for j in range(C_VALUE):
          item_id = index[j]
          if k > item_id:
            simvalues[k][j] = simvalues_item[item_id][k]
          else:
            simvalues[k][j] = simvalues_item[k][item_id]
    elif cl_type == 0:
      for k in range(len(IM_)):
        for j in range(C_VALUE):
          simvalues[k][j] = CAFCASimCal(patterns[j], IM_[k], DELAY_THRESHOLD)
    elif cl_type == 3:
      p = 0.2
      q = 0.8
      for j in range(C_VALUE):
        print("Run for " + str(j) + "th iteration")
        for k in range(len(IM_)):
          simvalues[k][j] = MTS(patterns[j], IM_[k], p, q)
    diss = 1 - simvalues
    print("============== Sim & Dissims Calculated")
    # print(diss)

    # Membership calculation
    if cl_type == 0 or cl_type == 3: # FCM
      for k in range(len(IM_)):
        temp = np.zeros(C_VALUE)
        for j in range(C_VALUE):
          if diss[k][j] == 0:
            memberships[k][j] = 1
          else:
            temp[j] = math.pow(diss[k][j], 2/(1-m))
        for j in range(C_VALUE):
          if temp[j] == 0:
            continue
          else:
            memberships[k][j] = temp[j] / sum(temp)
      # for j in range(C_VALUE):
      #   for k in range(len(IM_)):
      #     temp = 0
      #     for i in range(C_VALUE):
      #       if diss[i][k] == 0:
      #         continue
      #       temp += math.pow(diss[j][k] / diss[i][k], 2/(m-1))
      #     if temp == 0:
      #       memberships[j][k] = 1
      #     else:
      #       memberships[j][k] = 1 / temp
    else: # CAFCA & KS2M
      if iterations != 0:
        prev_memberships = copy.deepcopy(memberships)
      temp_numer = 0
      for k in range(len(IM_)):
        temp = []
        for i in range(C_VALUE):
          if cl_type == 1: # CAFCA
            val = math.pow(D(diss, prev_memberships, i, k, m, diss_item), 1 / (1 - m))
            temp.append(val)
          elif cl_type == 2:
            val = math.pow(D_KS2M(prev_memberships, i, k, m, diss_item), 1 / (1 - m))
            temp.append(val)
        for j in range(C_VALUE):
            memberships[k][j] = temp[j] / sum(temp)
    print("============== Memberships Calculated")
    # print(memberships)

    # Clustering
    clusters = [[] for j in range(C_VALUE)]
    for k in range(len(IM_)):
      max_idx = 0
      assign_flag = False
      for j in range(C_VALUE):
        if memberships[k][j] > SIM_THRESHOLD: # Clustering
          if not IMExistChecker(IM_[k], clusters[j]):
            clusters[j].append(IM_[k])
            assign_flag = True
      if not assign_flag:
        for i in range(C_VALUE):
          if memberships[k][i] > memberships[k][max_idx]:
            max_idx = i
        clusters[max_idx].append(IM_[k])
    print("============== Logs Clustered")
    # print(clusters)

    # Pattern update
    patterns.fill(None)
    GR_values = []
    if cl_type == 3:
      p = 0.2
      q = 0.8
      for j in range(C_VALUE):
        pattern = None
        random.shuffle(clusters[j]) # To make variation for the generated patterns
        for i in range(len(clusters[j])):
          pattern = MTSPattern(pattern, clusters[j][i], p, q, MIN_LEN_THRESHOLD)
        patterns[j] = copy.deepcopy(pattern)
    else:
      for j in range(C_VALUE):
        pattern = None
        random.shuffle(clusters[j]) # To make variation for the generated patterns
        # Discriminative pattern mining
        candidate_patterns = []
        for i in range(0,len(clusters[j]),2):
          if i+1 >= len(clusters[j]):
            break
          candidate_patterns.append(GetPattern(clusters[j][i], clusters[j][i+1], DELAY_THRESHOLD, MIN_LEN_THRESHOLD))
        if len(candidate_patterns) == 0:
          patterns[j] = copy.deepcopy(clusters[j][i])
        else:
          pattern, gr_value = DisCrimPattern(candidate_patterns, clusters[j], PIM_Batch, 0.8, DELAY_THRESHOLD) # APPEARANCE_THRESHOLD
          patterns[j] = copy.deepcopy(pattern)
          GR_values.append(gr_value)
        # for i in range(len(clusters[j])):
        #   pattern = GetPattern(pattern, clusters[j][i], DELAY_THRESHOLD, MIN_LEN_THRESHOLD)
        # patterns[j] = copy.deepcopy(pattern)
    print("============== Patterns Updated")
    # print(patterns)

    # Objective value calculation
    objs = 0.0
    if cl_type == 0 or cl_type == 3: #FCM
      for j in range(C_VALUE):
        for k in range(len(IM_)):
         objs += math.pow(memberships[k][j], m) * math.pow(diss[k][j],2)
    elif cl_type == 1: #CAFCA
      for j in range(C_VALUE):
        denom = 0.0
        numer = 0.0
        for k in range(len(IM_)):
          val = math.pow(memberships[k][j], m)
          objs += val * math.pow(diss[k][j],2)
          denom += val
          for l in range(len(IM_)):
            if k < l:
              numer += val * math.pow(memberships[l][j],m) * math.pow(diss_item[k][l],2)
            else:
              numer += val * math.pow(memberships[l][j], m) * math.pow(diss_item[l][k],2)
        objs += numer / denom
    else: #KS2M
      for j in range(C_VALUE):
        denom = 0.0
        numer = 0.0
        for k in range(len(IM_)):
          val = math.pow(memberships[k][j], m)
          denom += val
          for l in range(len(IM_)):
            if k < l:
              numer += val * math.pow(memberships[l][j],m) * math.pow(diss_item[k][l],2)
            else:
              numer += val * math.pow(memberships[l][j], m) * math.pow(diss_item[l][k],2)
        objs += numer / denom

    end_time = time.time()
    print("============== Objectives Calculated")
    # for p in range(C_VALUE):  # Initial version based on Fast Fuzzy Algorithm
    #   val = 0
    #   denom = 0
    #   for i,j in range(len(IM_)):
    #     val += math.pow(memberships[p][i], FUZZY_THRESHOLD) * math.pow(memberships[p][j], FUZZY_THRESHOLD) * diss[i][j]
    #     denom += math.pow(memberships[p][j],FUZZY_THRESHOLD)
    #   objs += val / 2 * denom

    # Evaluate the pattern mining & clustering results & Save them
    pit = PIT(ideal_patterns, patterns, 0.05, oracle_batch)
    pitw = PITW(ideal_patterns, patterns, 0.05, oracle_batch)
    f1p = EvaluateF1P(oracle_batch, IM_Index, clusters)
    pit_sum = 0
    for val in pit:
      if not val is None:
        pit_sum += val

    pitw_sum = 0
    for val in pitw:
      if not val is None:
        pitw_sum += val

    gr_result = ""
    if len(GR_values) == 0:
      GR_values = DisCrimPatternEval(patterns, clusters, PIM_Batch, 0.8, DELAY_THRESHOLD)
    for value in GR_values:
      gr_result += str(value) + ","
    gr_result = gr_result[:-1]
    print("d_threshold:" + str(DELAY_THRESHOLD) + ", " + "sim_threshold:" + str(SIM_THRESHOLD) + ", " + "iterations:" + str(iterations) + ", objs:" + str(objs) + "==> PIT:" + str(pit_sum) + ", PITW:" + str(pitw_sum) + ", F1P:" + str(f1p[-1]) + ", GR_Value:" + gr_result + ", Time:" + str((end_time - start_time)))

    ret = ""
    ret_pit = ""
    for val in pit:
      ret_pit += str(val) + ","
    ret_pitw = ""
    for val in pitw:
      ret_pitw += str(val) + ","
    ret += str(DELAY_THRESHOLD) + ", " + str(SIM_THRESHOLD) + ", " + str(iterations) + ", " + str(objs) + "," + str(pit_sum) + "," + ret_pit + str(pitw_sum) + "," + ret_pitw + str(f1p[-1]) + "," + gr_result  +  "," +(
              str(end_time - start_time)) + "\n"

    if prev_objs != -1 and abs(objs - prev_objs) < SENSITIVITY_THRESHOLD:
      break
    else:
      prev_objs = objs
    iterations += 1
  f.write(ret)
  # Silhouette Analysis
  print("============== Silhouette analysis ==============")
  if cl_type == 0:
    print("============== Item Comparison ==============")
    for k in range(len(IM_)):
      print("Run for " + str(k) + "th iteration")
      for l in range(len(IM_)):
        if k == l:
          simvalues_item[k][l] = 1.0
        elif k < l:
          simvalues_item[k][l] = CAFCASimCal(IM_[k], IM_[l], DELAY_THRESHOLD)

  silhouette = Silhouette(simvalues_item, IM_, clusters)
  f.write(str(silhouette) + "\n")
  f.close()
  return patterns, clusters

def DisCrimPatternEval(patterns, clusters, PIM_Batch, APPR_THRESHOLD, d_threshold):
  GR_values = []
  for i in range(len(patterns)):
    O_f = 0
    O_p = 0
    pattern = patterns[i]
    for im in clusters[i]: # Appearance checking on the failed & belonged cluster
      temp = CAFCASimCal(pattern, im,d_threshold)
      if temp > APPR_THRESHOLD:
        O_f += 1
    for im in PIM_Batch: # Appearance checking on the passed logs
      temp = CAFCASimCal(pattern, im, d_threshold)
      if temp > APPR_THRESHOLD:
        O_p += 1
    if O_p == 0:
      GR_values.append(1)
    else:
      GR_values.append((O_f / len(clusters[i]) / (O_p / len(PIM_Batch))))
  return GR_values

def DisCrimPattern(candidate_patterns, cluster, PIM_Batch, APPR_THRESHOLD, d_threshold):
  GR_values = []

  for pattern in candidate_patterns:
    O_f = 0
    O_p = 0
    for im in cluster: # Appearance checking on the failed & belonged cluster
      temp = CAFCASimCal(pattern, im,d_threshold)
      if temp > APPR_THRESHOLD:
        O_f += 1
    for im in PIM_Batch: # Appearance checking on the passed logs
      temp = CAFCASimCal(pattern, im, d_threshold)
      if temp > APPR_THRESHOLD:
        O_p += 1
    if O_p == 0:
      GR_values.append(1)
    else:
      GR_values.append((O_f / len(cluster) / (O_p / len(PIM_Batch))))

  GR_values = np.array(GR_values)
  return candidate_patterns[np.argmax(GR_values)], np.max(GR_values)

def Silhouette(simvalues_item, IM_, clusters):
  ret = 0.0
  sp = []

  for k in range(len(IM_)):
    a_i = 0.0
    b_list = []
    for j in range(len(clusters)):
      temp = 0.0
      if len(clusters[j]) == 0:
        continue
      for clustered_im in clusters[j]:
        index = GetIMIndex(clustered_im, IM_)
        if k < index:
          temp += simvalues_item[k][index]
        else:
          temp += simvalues_item[index][k]
      if IMExistChecker(IM_[k], clusters[j]):
        a_i = temp / len(clusters[j])
      else:
        b_list.append(temp / len(clusters[j]))
    if not b_list:
      b_i = 0
    else:
      b_i = min(b_list)
    sp.append((b_i - a_i) / max(a_i, b_i))
  return float(sum(sp)) / float(len(sp))

def GetIMIndex(im, IM_):
  for i in range(len(IM_)):
    if im[0] == IM_[i][0]:
      return i

def D(diss, prev_memberships, index_cluster, index_item, m, diss_item): #index_cluster: j , index_item: k
  ret = 0.0
  ret += math.pow(diss[index_item, index_cluster], 2)
  denom = 0.0
  numer = 0.0
  for h in range(len(diss_item)):
    if h == index_item:
      continue
    denom += math.pow(prev_memberships[h][index_cluster], m)
    if h < index_item:
      numer += math.pow(prev_memberships[h][index_cluster], m) * math.pow((diss_item[h][index_item]), 2)
    else:
      numer += math.pow(prev_memberships[h][index_cluster], m) * math.pow((diss_item[index_item][h]), 2)
  return ret + (numer/denom)

def D_KS2M(prev_memberships, index_cluster, index_item, m, diss_item): #index_cluster: j , index_item: k
  denom = 0.0
  numer = 0.0
  for h in range(len(diss_item)):
    if h == index_item:
      continue
    denom += math.pow(prev_memberships[h][index_cluster], m)
    if h < index_item:
      numer += math.pow(prev_memberships[h][index_cluster], m) * math.pow((diss_item[h][index_item]), 2)
    else:
      numer += math.pow(prev_memberships[h][index_cluster], m) * math.pow((diss_item[index_item][h]), 2)
  return numer/denom

def IMExistChecker(im, cluster):
  ret = False
  for clustered_im in cluster:
    if im[0] == clustered_im[0]:
      ret = True

  return ret

def IdealPatternReader():
  ideals = []
  for filename in os.listdir(IDEAL_PATH):
    interaction = []  # ======> interaction = [message0, message1, message2, ...] ordered chronologically
    env = [] # ==> [[time, [state0, state1, ..., state_n]], [time, [state0, ...]], ...]
    f = open(join(IDEAL_PATH,filename), 'r')
    lines = f.readlines()
    F_type = -1
    split_count = -1
    veh_roles = {}
    for i in range(3, len(lines)):  # For each line in log file
      message = []
      # ret_env = []
      ret_state = []
      line = lines[i]
      if ":" in line:
        line_items = line.split(":")
        # ret_env.append(line_items[0]) # time
        line_items[1] = line_items[1].replace("[", "")
        line_items[1] = line_items[1].replace("]", "")
        line_items[1] = line_items[1].replace("\n", "")
        line_items[1] = line_items[1].replace(" ", "")
        states = line_items[1].split(",")
        for state in states:
          ret_state.append(int(state))
        # ret_env.append(ret_state)
      else:
        line = ' '.join(line.split())  # Preprocessing
        line = line.replace(' -', '')
        line_items = line.split(' ')
        if 'MF_Leave' in line:  # FollowerLeave type checking for veh role analysis
          split_count = 2
        elif 'EF_Leave' in line:
          split_count = 1
        if len(line_items) > 5:  # For each message items => [time, command_sent, sender, sender_role, receiver, receiver_role] + weight
          time = line_items[0]
          message.append(time)
          command_sent = line_items[4]
          message.append(command_sent)
          if command_sent == 'MERGE_REQ':  # Role managmenet code by each role changing CS-level operations
            veh_roles[line_items[1]] = 'Leader'
            if line_items[5] not in veh_roles.keys() or veh_roles[line_items[5]] != 'Left':
              veh_roles[line_items[5]] = 'Leader'
          elif command_sent == 'SPLIT_REQ':
            if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
              veh_roles[line_items[1]] = 'Leader'
          elif command_sent == 'LEAVE_REQ':
            if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
              veh_roles[line_items[1]] = 'Left'
            if line_items[5] not in veh_roles.keys() or veh_roles[line_items[5]] != 'Left':
              veh_roles[line_items[5]] = 'Leader'
          elif command_sent == 'VOTE_LEADER':
            if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
              veh_roles[line_items[1]] = 'Left'
          # elif command_sent == 'ELECTED_LEADER':
          #   if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
          #     veh_roles[line_items[1]] = 'Leader'
          elif command_sent == 'MERGE_DONE':
            if line_items[1] not in veh_roles.keys() or veh_roles[line_items[1]] != 'Left':
              veh_roles.pop(line_items[1])
          elif command_sent == 'SPLIT_DONE':
            split_count -= 1
            if split_count != 0:  # Just SPLIT operation && the first SPLIT in MF-LEAVE && LEADER-LEAVE
              if line_items[5] not in veh_roles.keys() or veh_roles[line_items[5]] != 'Left':
                veh_roles[line_items[5]] = 'Leader'
            elif split_count == 0:  # The last SPLIT in MF-LEAVE / EF-LEAVE
              if line_items[5] not in veh_roles.keys() or veh_roles[line_items[5]] != 'Left':
                veh_roles[line_items[5]] = 'Left'
          sender = line_items[1]
          message.append(sender)
          if line_items[1] not in veh_roles.keys():
            message.append('Follower')
          else:
            message.append(veh_roles[line_items[1]])
          receiver = line_items[5]
          message.append(receiver)
          if line_items[5] not in veh_roles.keys():
            message.append('Follower')
          else:
            message.append(veh_roles[line_items[5]])
          if len(line_items) >= 10: # in Ideal pattern, some messages have weight
            message.append(line_items[9])

      if len(message) != 0:
        interaction.append(copy.deepcopy(message))
      # if len(ret_env) != 0:
        # env.append(ret_env)
      if len(ret_state) != 0:
        env.append(ret_state)
    f.close()
    interaction = np.array(interaction)
    pattern = []
    pattern.append(filename)
    pattern.append("False")
    pattern.append(copy.deepcopy(interaction))
    pattern.append(copy.deepcopy(env))
    ideals.append(copy.deepcopy(pattern))
  return np.array(ideals)

def PIT(ideal_patterns, patterns, d_threshold, oracle_batch):
  matched = []
  ret_PITs = []
  # id_index = [1,2,3,4] #OSR: [10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9]
  for idx, id_pattern in enumerate(ideal_patterns):
    # if len(oracle_batch[id_index[idx]-1]) == 0:
    #   ret_PITs.append(None)
    #   continue
    max_PIT = 0
    for idx_gen, gen_pattern in enumerate(patterns):
      if idx_gen in matched:
       continue
      env_sim = []
      lcs = GetPatternSimWithoutEnv(id_pattern, gen_pattern, d_threshold)[0][2]
      # lcs = GetPatternSim(id_pattern, gen_pattern, d_threshold)[0][2]
      if lcs is None:
        continue
      if len(id_pattern[3]) != 0:
        for state_a, state_b in zip(id_pattern[3], gen_pattern[3]):
            env_sim.append(EnvStateComparePIT(state_a, state_b))
      if len(env_sim) != 0:
        if max_PIT < (len(lcs) / len(id_pattern[2])) * 0.8 + np.nanmean(env_sim) * 0.2:
          max_PIT = (len(lcs) / len(id_pattern[2])) * 0.8 + np.nanmean(env_sim) * 0.2
          # matched_id = idx_gen
      else:
        if max_PIT < (len(lcs) / len(id_pattern[2])):
          max_PIT = (len(lcs) / len(id_pattern[2]))
    # matched.append(matched_id)
    ret_PITs.append(max_PIT)

  return ret_PITs

def PITW(ideal_patterns, patterns, d_threshold, oracle_batch):
  matched = []
  ret_PITWs = []
  # id_index = [1,2,3,4] #OSR: [10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9]
  for idx, id_pattern in enumerate(ideal_patterns):
    # if len(oracle_batch[id_index[idx]-1]) == 0:
    #   ret_PITWs.append(0)
    #   continue
    max_PITW = 0
    for idx_gen, gen_pattern in enumerate(patterns):
      if idx_gen in matched:
        continue
      lcs = GetPatternSimWithoutEnv(id_pattern, gen_pattern, d_threshold)[0][2]
      if lcs is None:
        continue
      weight_lcs = 0
      env_sim = []
      for message in lcs:
        if len(message) >= 7:
          weight_lcs += int(message[6])
      weight_id = 0
      for message in id_pattern[2]:
        if len(message) >= 7:
          weight_id += int(message[6])
      if len(id_pattern[3]) != 0:
        for state_a, state_b in zip(id_pattern[3], gen_pattern[3]):
          env_sim.append(EnvStateComparePIT(state_a, state_b))
      if len(env_sim) != 0:
        PITW = ((len(lcs) + weight_lcs) / (len(id_pattern[2]) + weight_id)) * 0.8 + np.nanmean(env_sim) * 0.2
      else:
        PITW = ((len(lcs) + weight_lcs) / (len(id_pattern[2]) + weight_id))
      if max_PITW < PITW:
        max_PITW = PITW
        # matched_id = idx_gen
    # matched.append(matched_id)
    ret_PITWs.append(max_PITW)

  return ret_PITWs

"""# **Extended SBFL for Pattern Elaboration**

Extend SBFL approach to make the patterns more elaborative using failed & passed logs

## SBFL Executor
"""

import math
def CheckPatternAppearance_ESMIC(pattern, interaction_model, pattern_prev, interaction_model_prev, pattern_env, interaction_model_env, d_threshold):
  result = False
  if len(pattern)==0: #Initial point of recursive call
    return True
  else:
    head = pattern[0]
    tail = pattern[1:]
    for i in range(len(interaction_model)):
      if ESMIC(head, interaction_model[i], pattern_prev, interaction_model_prev, pattern_env, interaction_model_env, d_threshold, 5, 0.8): #Comparison of head message of pattern and current message in interaction model
        result = CheckPatternAppearance(tail, interaction_model[i+1:], head, interaction_model[i], pattern_env, interaction_model_env, d_threshold, 5, 0.8) #If exist, check rest of the pattern and rest of the interaction model
        break
    return result

def CheckPatternAppearance(pattern, interaction_model): # If for LCS: len(LCS(Pattern, interaction_model)) / len(Pattern)
  result = False

  if len(pattern)==0: #Initial point of recursive call
    return True
  else:
    head = pattern[0]
    tail = pattern[1:]
    for i in range(len(interaction_model)):
      if MCT(head,interaction_model[i]): #Comparison of head message of pattern and current message in interaction model
        result = CheckPatternAppearance(tail, interaction_model[i+1:]) #If exist, check rest of the pattern and rest of the interaction model
        break
    return result

def CheckNumberofPassFail(pattern, IM):
  numpass = 0
  numfail = 0
  for i in IM: #For all im in IM, check appearance and count pass and fail cases when pattern appears in im.
    if CheckPatternAppearance(pattern,i[2]):
      if i[1]=="FALSE":
        numfail += 1
      else:
        numpass += 1
  return (numpass,numfail)

def SBFLScore(technique,numpass,numfail,IM):
  totalpassed=0
  totalfailed=0
  for i in IM:
    if i[1] == "FALSE":
      totalfailed += 1
    else:
      totalpassed += 1
  if technique=="Tarantula":
    if numfail== 0 and numpass ==0: return 0
    return (numfail/totalfailed)/((numfail/totalfailed)+(numpass/totalpassed))
  elif technique == "Ochiai":
    if numfail== 0 and numpass ==0: return 0
    return numfail/math.sqrt(totalfailed*(numfail+numpass))
  elif technique == "Op2":
    return numfail - (numpass/(totalpassed+1))
  elif technique == "DStar":
    if numpass+(totalfailed-numfail)== 0: return math.inf
    return math.pow(numfail,x)/(numpass+(totalfailed-numfail))

def SBFL(patterns,IM,n,technique):
  patternscorelist = []
  for i in patterns:
    p,f = CheckNumberofPassFail(i,IM)
    print(p,f)
    score = SBFLScore(technique,p,f,IM)
    patternscorelist.append((i,score))
  patternscorelist.sort(key=lambda x:-x[1])
  return patternscorelist[0:n]

def RunSBFL(IM):
  print(IM[0])
  print(len(IM))
  print(SBFL([[["0.00","SPLIT_REQ","veh","Leader","veh.4","Follower"], ["0.00","SPLIT_REQ","veh1","Leader","veh1.4","Follower"]]],IM,1,"Tarantula"))
  print(SBFL([IM[0][2]],IM,1,"Tarantula"))

"""# **Evaluation**"""

#F1P Evaluator

import math

def sumContributionsIM(elements,elem_clusters): #element: [InteractionModel], elem_clusters: Dict: str - [int]
    ret = 0

    for elem in elements:
        shares_elem = len(elem_clusters[elem[0]])
        ret += 1 / shares_elem

    return ret

def sumContributions(elements,elem_clusters): #element: [str], elem_clusters: Dict: str - [int]
    ret = 0

    for elem in elements:
        shares_elem = len(elem_clusters[elem])
        if shares_elem != 0:
          ret += 1/ shares_elem

    return ret

def matchedElements(cl_cl,cl_or):
    matched = []

    for im in cl_cl:
        for elem in cl_or:
            if im[0] == elem: matched.append(im[0])

    return matched


def EvaluateF1P(oracle,index,cluster): #oracle: [[str]], index: [str], cluster: [[InteractionModel]]
    ret = []
    c_element_index = {} #Dictionary of the set of location of each Interaction model in cluster
    o_element_index = {} #Dictionary of the set of location of each Interaction model in oracle (Ground-truth)

    #Generate Element-wise dictionary of Oracle and the formed cluster
    for id in index:
        c_index  = []
        o_index = []

        for idx, cl in enumerate(oracle):
            if(id in cl): o_index.append(idx)

        for idx, IMs in enumerate(cluster):
            for IM in IMs:
                if IM[0] == id:
                  c_index.append(idx) #IM[0] : id of the IM

        o_element_index[id] = o_index
        c_element_index[id] = c_index

    bestMatches_cl = []
    bestMatches_or = []
    bestMatch = 0
    cl_cl_cntb = 0
    cl_or_cntb = 0
    matched_cntb = 0
    tempMatch = 0

    #Formed cluster의 결과에서 단일 cluster를 기준으로 oracle에서 가장 Best한 match값을 가지는
    #oracle_cluster 와의 contribution sum을 해당 cluster의 match값으로 설정함. -> F_(C,O)

    for cl_cl in cluster: #cl_cl: [InteractionModel]
        for cl_or in oracle: #cl_or: [str]
            cl_cl_cntb = sumContributionsIM(cl_cl,c_element_index)
            cl_or_cntb = sumContributions(cl_or, o_element_index)
            matched = matchedElements(cl_cl,cl_or)

            matched_cntb = sumContributions(matched,c_element_index)

            if (cl_cl_cntb * cl_or_cntb) == 0:
              tempMatch = 0
            else:
              tempMatch = math.pow(matched_cntb,2) / (cl_cl_cntb*cl_or_cntb)
            if tempMatch > bestMatch:
                bestMatch = tempMatch
        bestMatches_cl.append(math.sqrt(bestMatch))
        bestMatch = 0

    F_C_O = 0
    for mat in bestMatches_cl:
        F_C_O += mat/len(bestMatches_cl)

    #F_C_O *= (1/0.7) #What is this?

    ret.append(F_C_O)

    for cl_or in oracle:
        for cl_cl in cluster:
            cl_cl_cntb = sumContributionsIM(cl_cl,c_element_index)
            cl_or_cntb = sumContributions(cl_or,o_element_index)
            matched = matchedElements(cl_cl,cl_or)

            matched_cntb = sumContributions(matched,o_element_index)

            if (cl_cl_cntb * cl_or_cntb) == 0:
              tempMatch = 0
            else:
              tempMatch = math.pow(matched_cntb, 2) / (cl_cl_cntb * cl_or_cntb)
            if tempMatch > bestMatch:
                bestMatch = tempMatch
        bestMatches_or.append(math.sqrt(bestMatch))
        bestMatch = 0

    F_O_C = 0
    for mat in bestMatches_or:
        F_O_C += mat/len(bestMatches_or)

    #F_O_C *= (1/0.7)

    ret.append(F_O_C)
    ret.append(2*F_C_O*F_O_C/(F_C_O+F_O_C))

    return ret

def RunFCM(IM_, oracle, exp_type, PIM_): # exp_type : 0 -> OSR 1 -> COLL
  # IM Selection (Random)
  nIM_ = np.array(IM_)
  nPIM_ = np.array(PIM_)
  j = 1
  for i in range(12):
    if exp_type == 0:
      np.random.shuffle(nIM_)
      IM_Batch = nIM_[0:100]
      IM_Index = []
      for im in IM_Batch:
        IM_Index.append(im[0])
      # C_VALUE setting codes by the randomly selelcted subset
      C_VALUE = 0
      oracle_batch = []
      for cl in oracle:
        cl_batch = []
        assign_flag = False
        for im in IM_Batch:
          if str(im[0])+"_0" in cl:
            assign_flag = True
            cl_batch.append(im[0])
        if assign_flag:
          C_VALUE += 1
        oracle_batch.append(copy.deepcopy(cl_batch))
      ideal_patterns = IdealPatternReader()
    else:
      np.random.shuffle(nIM_)
      IM_Batch = []
      IM_Index = []
      oracle_batch = []
      C_VALUE = 4
      for im in nIM_:
        for cl in oracle:
          if str(im[0]) + "_0" in cl:
            IM_Batch.append(im)
            IM_Index.append(im[0])
            break
      for cl in oracle:
        cl_batch = []
        assign_flag = False
        for im in IM_Batch:
          if str(im[0]) + "_0" in cl:
            assign_flag = True
            cl_batch.append(im[0])
        if assign_flag:
          oracle_batch.append(copy.deepcopy(cl_batch))
      IM_Batch = np.array(IM_Batch)
      ideal_patterns = IdealPatternReader()[:-2]

    np.random.shuffle(nPIM_)
    PIM_Batch = nPIM_[0:100]
    # Run FCM with hyperparam settings
    # for DELAY_THRESHOLD in range(1, 11):
    # start_time = time.time()

    if i != 0 and i % 3 == 0:
      j += 1
    if exp_type == 0: # OSR // 0: FCM, 1: CAFCA, 2:KS2M
      patterns, clusters = FCM(0, IM_Batch, 0.05, (1/C_VALUE) + (0.1*j), 4+(3*(i%3)), C_VALUE, ideal_patterns, oracle_batch, IM_Index, PIM_Batch)
    elif exp_type == 1: # COLL // 0: FCM, 1: CAFCA, 2:KS2M
      patterns, clusters = FCM(1, IM_Batch, 0.05, (1/C_VALUE) + (0.1*j), 4+(3*(i%3)), C_VALUE, ideal_patterns, oracle, IM_Index, PIM_Batch)
    # end_time = time.time()

  # Evaluate the pattern mining & clustering results
  # pit = PIT(ideal_patterns, patterns, 0.05, 10)
  # pitw = PITW(ideal_patterns, patterns, 0.05, 10)
  # f1p = EvaluateF1P(oracle_batch, IM_Index, clusters)
  # print(0.5 + ", " +  1/C_VALUE + ": " +sum(pit) +"," + sum(pitw) + "," + f1p[-1] + "," + (end_time - start_time))
  # f = open(join(V_PATH, "FCM_0.csv"), 'w')
  # ret = ""
  # ret_pit = ""
  # for val in pit:
  #   ret_pit += val + ","
  # ret_pitw = ""
  # for val in pitw:
  #   ret_pitw += val + ","
  # ret += 0.5 + ", " +  1/C_VALUE + "," + sum(pit) +"," + ret_pit + sum(pitw) + "," + ret_pitw + f1p[-1] + "," + (end_time - start_time) + "\n"
  # f.write(ret)
  # f.close()

def main():
  IM, FIM, classification_data, PIM = IMGenerator()
  # IMtoTxt(IM,'InteractionModels.txt')
  # IMtoTxt(FIM, 'FailedInteractionModels.txt')
  # FIM = TxttoIM('FailedInteractionModels.txt')

  # RunSPADE(FIM)
  # RunLogLiner(FIM, classification_data)
  # RunFCM(FIM, classification_data[:-2], 1) # 0 : OSR, 1 : COLL
  RunFCM(FIM, classification_data, 1, PIM) # 0 : OSR, 1 : COLL

if __name__ == "__main__":
  main()
