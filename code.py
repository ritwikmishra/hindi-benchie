import re
import json
import copy
import string

def compare_clean_golden_ext_with_oie_ext(ext_g,ext_oie):
	ext_oie = ext_oie.split('\t')
	# print('here '*50)
	# print(ext_g, len(ext_g))
	# print(ext_oie, len(ext_oie))
	assert len(ext_g) == len(ext_oie)
	# sl = []
	bw = []
	for g,o in zip(ext_g,ext_oie):
		ol = o.split()
		gl = g.split()
		tbw = []
		i,j = 0,0
		# print(g)
		# print(o)
		while i < len(ol) and j < len(gl):
			# print(i,len(ol),j,len(gl))
			if ol[i]!=re.sub(r'\]|\[|\{[a-z]+\}','',gl[j]): # match failed
				# print('not matched')
				# print(ol[i],'vs',gl[j])
				if '[' == gl[j][0]:
					bracket_start, bracket_end = j, j
					while ']' not in gl[bracket_end]:
						bracket_end+=1
					if '{' in gl[bracket_end] and '}' in gl[bracket_end]:
						tbw.append(re.search(r'\{[a-z]+\}',gl[bracket_end])[0][1:-1])
					gl = gl[:bracket_start]+gl[bracket_end+1:]
					continue
				else:
					break
			else:
				# print('matched')
				# print(ol[i])
				i+=1
				j+=1
		if i == len(ol):
			while j != len(gl) and '[' == gl[j][0]:
				bracket_start, bracket_end = j, j
				while ']' not in gl[bracket_end]:
					bracket_end+=1
				if '{' in gl[bracket_end] and '}' in gl[bracket_end]:
					tbw.append(re.search(r'\{[a-z]+\}',gl[bracket_end])[0][1:-1])
				gl = gl[:bracket_start]+gl[bracket_end+1:]
			if j == len(gl):
				bw+=tbw
				# sl.append('satisfied')
			else:
				return 'not satisfied'
		else:
			return 'not satisfied'
	if bw:
		# print(bw)
		# input('wait')
		return 'satisfied but with '+','.join(bw)
	else:
		return 'satisfied'

def compare_raw_golden_ext_with_oie_ext(ext_golden, ext_oie, default_passive):
	ext_golden = ext_golden.split(' |OR| ')
	# print('raw',ext_golden)
	# print('raw',ext_oie)
	bl = []
	for ext_g in ext_golden:
		if ' <--{not allowed in passive}' in ext_g:
			passive = False
			ext_g = ext_g.replace(' <--{not allowed in passive}','')
		elif ' <--{allowed in passive}' in ext_g:
			passive = True
			ext_g = ext_g.replace(' <--{allowed in passive}','')
		elif ' <--{' in ext_g:
			print('Unknown command found in "'+ext_g+'"\nExiting')
			exit()
		else:
			passive = default_passive

		ext_g = ext_g.split(' --> ')
		b2 = ''
		b = compare_clean_golden_ext_with_oie_ext(ext_g, ext_oie)
		if b=='satisfied':
			return b
		if passive and b!='satisfied':
			t = ext_g[2]
			ext_g[2] = ext_g[0]
			ext_g[0] = t
			b2 = compare_clean_golden_ext_with_oie_ext(ext_g, ext_oie)
			if b2 == 'satisfied':
				return b2
		if 'satisfied but' in b:
			bl.append(b)
		else:
			bl.append(b2)
		
	bl2 = []
	for x in bl:
		if 'satisfied but' in x:
			bl2.append(x)
	if bl2:
		b = ' |OR| '.join(bl2) # now that I think hard, I realize that there will never be a situation where one extraction satisfies more than one pattern connected by |OR|
	else:
		b = 'not satisfied'
	return b

def n_extractions_in_smallest_cluster(golden_dict, n_sent):
	ext_g = golden_dict[n_sent]
	n = 0
	for cluster_no in ext_g.keys():
		n = max(len(ext_g[cluster_no]['essential']),n)
	return n

def calc_metrics(gold, exts, default_passive = True, show = False):
	golden_dict = {}
	essential_exts, compensating_dict, cluster_number, cluster_dict, sentence_number = [], {}, '', {}, ''

	for i,line in enumerate(gold):
		if 'sent_id:' in line:
			if sentence_number:
				ext_dict = {'essential':essential_exts, 'compensatory': compensating_dict}
				cluster_dict['cluster '+cluster_number] = ext_dict
				golden_dict['sent '+sentence_number] = cluster_dict
				essential_exts, compensating_dict, cluster_number, cluster_dict = [], {}, '', {}
				# print(json.dumps(golden_dict,indent=2,ensure_ascii=False).encode('utf8').decode() )
				# input('wait')
			sentence_number = re.search(r'sent_id:\d+',line)[0][8:]
			golden_dict['s'+sentence_number+' txt'] = line.split('\t')[1]
		elif '------ Cluster' in line:
			if cluster_number:
				ext_dict = {'essential':essential_exts, 'compensatory': compensating_dict}
				cluster_dict['cluster '+cluster_number] = ext_dict
				essential_exts, compensating_dict = [], {}
			cluster_number = re.search(r'\d+',line)[0]
		elif re.search(r'\{[a-z]\}',line[:4]):
			compensating_dict[line[1]] = line[4:]
		elif '='*20 not in line:
			essential_exts.append(line)

	ext_dict = {'essential':essential_exts, 'compensatory': compensating_dict}
	cluster_dict['cluster '+cluster_number] = ext_dict
	essential_exts, compensating_dict = [], {}
	golden_dict['sent '+sentence_number] = cluster_dict
	essential_exts, compensating_dict, cluster_number, cluster_dict = [], {}, '', {}

	if show:
		pass
		# print('Golden dictionary is')
		# print(json.dumps(golden_dict,indent=2,ensure_ascii=False).encode('utf8').decode()[:500]+'\n\t... ... ...'*3)

	# --- Gathering extractions ---
	ext_oie = {}
	for e in exts:
		e = e.split('\t')
		sno = e[0]
		e = re.sub(' +',' ','\t'.join(e[1:]))
		e = e.translate(str.maketrans('', '', string.punctuation+'।'))
		e = re.sub(' +',' ',e)
		try:
			if e not in ext_oie[sno]: # removes duplicates
				ext_oie[sno].append(e)
		except Exception as ex:
			ext_oie[sno] = [e]

	# print(ext_oie)
	if show:
		print('\nExtractions to evaluate are')
		print(json.dumps(ext_oie,indent=2,ensure_ascii=False).encode('utf8').decode()[:500]+'\n\t... ... ...'*3 )
		print('Total sents',len(ext_oie.keys()))

	golden_state_dict = copy.deepcopy(golden_dict)

	tpl, fpl, fnl = [], [], []

	# --- Populating the state dict ---
	for k in ext_oie.keys():
		ext_l = ext_oie[k] # ext_l is extractions of one sentence
		sno = k
		sent_dict = golden_dict['sent '+sno]
		state_dict = golden_state_dict['sent '+sno]
		tp, fp = 0, len(ext_l)
		for e in ext_l:
			tp_dict = {e:False}
			for cluster_no in sent_dict.keys():
				# print('-'*100)
				# print('sent',k,'cluster',cluster_no,'oie',e)
				for i,ext_g in enumerate(sent_dict[cluster_no]['essential']):
					if 'satisfied' not in state_dict[cluster_no]['essential'][i]:
						state_dict[cluster_no]['essential'][i] = 'not satisfied' # filling "not satisfied" by default
					elif state_dict[cluster_no]['essential'][i] == 'satisfied':
						continue # already satisfied, hence do not check this # it adds one additional feature i.e. if one extraction satisfies a particular pattern, then another cannot do it. Hence repetitive extractions are penalized.
					curr_state = compare_raw_golden_ext_with_oie_ext(ext_g, e, default_passive)
					if curr_state != 'not satisfied': # i.e. the extraction matched
						tp_dict[e] = True
					if curr_state == 'satisfied':
						state_dict[cluster_no]['essential'][i] = curr_state
					elif 'satisfied but' in curr_state:
						if 'satisfied but' in state_dict[cluster_no]['essential'][i]:
							state_dict[cluster_no]['essential'][i] += '|AND|'+curr_state
						else:
							state_dict[cluster_no]['essential'][i] = curr_state
					# else:
					# 	state_dict[cluster_no]['essential'][i] = curr_state

				for ck in sent_dict[cluster_no]['compensatory'].keys():
					ext_g = sent_dict[cluster_no]['compensatory'][ck]
					if 'satisfied' not in state_dict[cluster_no]['compensatory'][ck]:
						state_dict[cluster_no]['compensatory'][ck] = 'not satisfied'
					elif state_dict[cluster_no]['compensatory'][ck] == 'satisfied':
						continue
					curr_state = compare_raw_golden_ext_with_oie_ext(ext_g, e, default_passive)
					if curr_state != 'not satisfied': # i.e. the extraction matched
						tp_dict[e] = True
					if curr_state == 'satisfied':
						state_dict[cluster_no]['compensatory'][ck] = curr_state
					elif 'satisfied but' in curr_state:
						if 'satisfied but' in state_dict[cluster_no]['compensatory'][ck]:
							state_dict[cluster_no]['compensatory'][ck] += '|AND|'+curr_state
						else:
							state_dict[cluster_no]['compensatory'][ck] = curr_state
			if tp_dict[e]:
				tp+=1
			if show:
				print('The state of golden dict after processing of this extraction ("'+e+'"): ')
				print(json.dumps(state_dict,indent=2,ensure_ascii=False).encode('utf8').decode())
		tpl.append(tp)
		fpl.append(fp-tp)
		if show:
			print('After processing all the extractions')
			print(ext_l)
			print('The state of golden dict is (of this sentence)')
			print(json.dumps(state_dict,indent=2,ensure_ascii=False).encode('utf8').decode())

	if show:
		pass
		# print('\nState of golden dictionary after processing extractions is')
		# print(json.dumps(golden_state_dict,indent=2,ensure_ascii=False).encode('utf8').decode()[:500]+'\n\t... ... ...'*3 )


	def fn_sb(cd,cel,fn=0):
		i = 0
		while i < len(cel):
			ce = cel[i]
			if 'not satisfied' == cd[ce]:
				fn+=1
				cd[ce] = 'X'
			elif 'satisfied but' in cd[ce]:
				cel2 = cd[ce].split()[-1].split(',')
				fn = fn_sb(cd,cel2,fn)
			i+=1
		return fn


	for sno in ext_oie.keys():
		# --- Take one cluster at a time, and select the minimum number of FN ---
		temp_fn = []
		for cluster_no in golden_state_dict['sent '+sno].keys():
			# print(cluster_no)
			# input('wait')
			cluster = golden_state_dict['sent '+sno][cluster_no]
			fn = 0
			for e in cluster['essential']:
				if e == 'not satisfied':
					fn+=1
				if 'satisfied but' in e:
					tfnl = []
					for e2 in e.split('|AND|'):
						cel = e2.split()[-1].split(',')
						tfnl.append(fn_sb(cluster['compensatory'].copy(),cel))
					fn += min(tfnl)

					# cel = e.split()[-1].split(',')
					# fn += fn_sb(cluster['compensatory'].copy(),cel)
			temp_fn.append(fn)
		fnl.append(min(temp_fn))
		# if 'sent ' in sno:
			# fn = 0
			# cluster_with_most_satisfied = (0,'cluster 1')
			# for cluster_no in golden_state_dict[sno].keys():
			# 	cluster = golden_state_dict[sno][cluster_no]
			# 	satno = 0
			# 	for e in cluster['essential']:
			# 		if 'satisfied' == e or 'satisfied but' in e:
			# 			satno+=1
			# 	for k in cluster['compensatory'].keys():
			# 		if 'satisfied but' in cluster['compensatory'][k] or 'satisfied' == cluster['compensatory'][k]:
			# 			satno+=1
			# 	if satno > cluster_with_most_satisfied[0]:
			# 		cluster_with_most_satisfied = (satno, cluster_no)
			# print('cluster_with_most_satisfied',cluster_with_most_satisfied[1],cluster_with_most_satisfied[0])

			# cluster = golden_state_dict[sno][cluster_with_most_satisfied[1]]
			# for e in cluster['essential']:
			# 	if e == 'not satisfied':
			# 		fn+=1
			# 	if 'satisfied but' in e:
			# 		cel = e.split()[-1].split(',')
			# 		fn += fn_sb(cluster['compensatory'].copy(),cel)
			# fnl.append(fn)

	missing_fn = []
	for sent_n in golden_dict.keys():
		if sent_n.split()[-1] not in ext_oie.keys() and 'txt' not in sent_n:
			missing_fn.append(n_extractions_in_smallest_cluster(golden_dict,sent_n))



	# p = []
	# r = []
	# fl = []
	# for tp, fp, fn in zip(tpl,fpl,fnl):
	# 	if tp == 0:
	# 		p.append(0)
	# 		r.append(0)
	# 		fl.append(0)
	# 	else:
	# 		precision = tp/(tp+fp)
	# 		recall = tp/(tp+fn)
	# 		p.append(precision)
	# 		r.append(recall)
	# 		fl.append(2*(precision*recall)/(precision+recall))

	# print('Recall',sum(r)/len(r))
	# print('Precision',sum(p)/len(p))
	# print('F-score',sum(fl)/len(fl))

	p = sum(tpl)/(sum(tpl)+sum(fpl)) if (sum(tpl)+sum(fpl)) != 0 else 0
	r = sum(tpl)/(sum(tpl)+sum(fnl)+sum(missing_fn)) if (sum(tpl)+sum(fnl)+sum(missing_fn)) != 0 else 0
	f = 2*p*r/(p+r) if (p+r) != 0 else 0

	print('TP',tpl,len(tpl))
	print('FP',fpl)
	print('FN',fnl)
	print('Missing FNs',missing_fn)

	print('Recall',r)
	print('Precision',p)
	print('F-score',f)

	return r,p,f

## ----- a small stub to calculate hindi_benchie scores on the english sample ----- 
# file = open('extractions/english_explicit.text','r')
# exts = [x.strip() for x in file.readlines()]
# file.close()
# file = open('english_benchie_gold.txt','r')
# gold = [x.strip() for x in file.readlines()]
# file.close()
# print(calc_metrics(gold, exts))
# exit()

import glob
ml = glob.glob('extractions/*.txt')
default_passive = True
show = False

nms, pl, rl, fl = [], [], [], []

file = open('hindi_benchie_gold.txt','r')
gold = [x.strip() for x in file.readlines()]
file.close()

for fname in ml:
	print('-'*100,fname,'-'*100)
	nms.append(fname.replace('extractions/',''))
	file = open(fname,'r')
	exts = [x.strip() for x in file.readlines()]
	file.close()

	r, p, f = calc_metrics(gold, exts)
	rl.append(r)
	pl.append(p)
	fl.append(f)

import matplotlib.pyplot as plt
import numpy as np

fig = plt.figure()

x = np.arange(1,2+(len(nms)-1)*5,5)
y = rl
plt.bar(x,y)

x = np.arange(2,3+(len(nms)-1)*5,5)
y = pl
plt.bar(x,y)

x = np.arange(3,4+(len(nms)-1)*5,5)
y = fl
plt.bar(x,y)

x = np.arange(2,3+(len(nms)-1)*5,5)
plt.xticks(x,nms)

plt.legend(['recall','precision','f-score'])

plt.show()

