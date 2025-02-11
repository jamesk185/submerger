# Author: James Kowalik
# Created: 25/01/12
# Revised: 25/02/11
# Description: Merge two srt files of different languages

# TODO; consider case where first_sub runs out of subs before second_sub (maybe already OK?)
# TODO eventually; create system of rules for whether adjacent merged subs are different speakers or not
# TODO maybe; get optimum final subtitle
# TODO; optimise code for beauty and speed

import re
import datetime as dt
from datetime import datetime
import sys


def parse_subs(text, which):
	# initialise
	prevline = "blank"
	content = ""
	subs_dict = {}
	
	# initialise marker to indicate whether content is from first or second sub
	if which == "first":
		marker = "{{1}}"
	elif which == "second":
		marker = "{{2}}"
	
	# loop through text line by line
	for count, line in enumerate(text):
		line = line.strip()
		
		# line is subtitle number so start new block
		if line.isnumeric() and prevline == "blank":
			id = line
			prevline = "id"
		# line is time stamp
		elif " --> " in line and prevline == "id":
			start_time, end_time = line.split(" --> ")
			# parse the timestamps
			start_time = datetime.strptime(start_time, time_format)
			end_time = datetime.strptime(end_time, time_format)
			prevline = "time"
		# line is text
		elif line and prevline in ["time", "content"]:
			content += " " + line
			content = content.strip()
			prevline = "content"
		# line is blank so start new block
		elif not line:
			# add to all block's data to dict
			if id not in subs_dict:
				subs_dict[id] = (start_time, end_time, content + marker)
			else:
				print(f"ID used a second time on line {count}. Exited early")
				sys.exit()
			content = ""
			prevline = "blank"
		# unknown
		else:
			print(f"Issue on line {count}. Exited early")
	
	return subs_dict


def merge_subs(first_sub, second_sub):
	
	newid = 1
	out = ""
	unmatched_second_sub = []
	
	# create lists for both
	first_sub_list = [(value, key) for key, value in first_sub.items()]
	second_sub_list = [(value, key) for key, value in second_sub.items()]
	
	# find starting sub ID in second_sub
	for i in range(3):
		# getting starting time in first_sub
		start_time = first_sub_list[i][0][0]
		# find starting point in second_sub
		starting_second_sub = [x[1] for x in second_sub_list if dates2seconds_diff(x[0][0], start_time) < 0.5]
		if starting_second_sub:
			starting_second_sub = starting_second_sub[0]
			starting_first_sub = first_sub_list[i][1]
			break
		elif not starting_second_sub and i == 2:
			print("Could not find the starting point in the second file.")
			sys.exit()
	
	# remove subs that come before the starting points
	first_sub_list = [x for x in first_sub_list if int(x[1]) >= int(starting_first_sub)]
	second_sub_list = [x for x in second_sub_list if int(x[1]) >= int(starting_second_sub)]
	
	while first_sub_list:
		done = None
		
		# initialise first_sub objects
		sub, key = first_sub_list[0]
		first_start_time = sub[0]
		first_end_time = sub[1]
		first_content = sub[2]
		
		# initialise second_sub objects
		if not second_sub_list:
			out += str(newid) + "\n" + first_start_time.strftime(time_format) + " --> " + first_end_time.strftime(time_format) + "\n" + first_content + "\n\n"
			first_sub_list = first_sub_list[1:]
			newid += 1
			continue
		second_start_time = second_sub_list[0][0][0]
		second_end_time = second_sub_list[0][0][1]
		second_content = second_sub_list[0][0][2]
		
		# 1) difference between start times is less than 2.75s
		if dates2seconds_diff(second_start_time, first_start_time) > 2.75:
			# find next matching sub in second_sub
			only_second_sub = []
			# assume there wouldn't be as many as 5 subsequent subtitles with no match
			for i in range(5):
				# match found
				if dates2seconds_diff(second_sub_list[i][0][0], first_start_time) < 2.75:
					second_sub_list = second_sub_list[i:]
					break
				# add to list of unmatched to be outputted as stand alone subs
				else:
					only_second_sub.append(second_sub_list[i])
					# if no break point found assume there is no match at all
					if i == 4:
						only_second_sub = None
			# a) if still no match on second_sub then output only first_sub
			if not only_second_sub:
				print(f"No good starting point for first sub {key}")
				# add to output text with no match
				out += str(newid) + "\n" + first_start_time.strftime(time_format) + " --> " + first_end_time.strftime(time_format) + "\n" + first_content + "\n\n"
				newid += 1
				first_sub_list = first_sub_list[1:]
				continue
			# b) if match on second sub in second_sub then move forward adding the first sub in the unmatched pile
			# also add first_sub to output as it's likely a situation like a scene with spoken English that naturally only needs to be translated in the other language
			else:
				for unmatched_sub in only_second_sub:
					unmatched_second_sub.append(unmatched_sub)
					out += str(newid) + "\n" + unmatched_sub[0][0].strftime(time_format) + " --> " + unmatched_sub[0][1].strftime(time_format) + "\n" + unmatched_sub[0][2] + "\n\n"
					newid += 1
				# get second_sub objects from new starting point
				second_start_time = second_sub_list[0][0][0]
				second_end_time = second_sub_list[0][0][1]
				second_content = second_sub_list[0][0][2]
		
		# 2) difference between end times is less than 0.75s
		out, done, second_sub_list = endtime_diff(0.75, newid, second_sub_list, first_start_time, second_start_time, first_end_time, second_end_time, first_content, second_content, out, done)
		if done:
			newid += 1
			first_sub_list = first_sub_list[1:]
			continue
		
		# 3) adjacent merged sub differs by less than 0.75s
		out, done, second_sub_list = merged_endtime_diff(0.75, newid, second_sub_list, first_start_time, second_start_time, first_end_time, first_content, second_content, out, done)
		if done:
			newid += 1
			first_sub_list = first_sub_list[1:]
			continue
		
		# 4) difference between end times is less than 1.5s
		out, done, second_sub_list = endtime_diff(1.5, newid, second_sub_list, first_start_time, second_start_time, first_end_time, second_end_time, first_content, second_content, out, done)
		if done:
			newid += 1
			first_sub_list = first_sub_list[1:]
			continue
		
		# 5) adjacent merged sub differs by less than 1.5s
		out, done, second_sub_list = merged_endtime_diff(1.5, newid, second_sub_list, first_start_time, second_start_time, first_end_time, first_content, second_content, out, done)
		if done:
			newid += 1
			first_sub_list = first_sub_list[1:]
			continue
		
		# 6) REVERSED adjacent merged sub differs by less than 0.75s
		out, done, first_sub_list = merged_endtime_diff(0.75, newid, first_sub_list, second_start_time, first_start_time, second_end_time, second_content, first_content, out, done, "yes")
		if done:
			newid += 1
			second_sub_list = second_sub_list[1:]
			continue
		
		# 7) REVERSED adjacent merged sub differs by less than 1.25s
		out, done, first_sub_list = merged_endtime_diff(1.25, newid, first_sub_list, second_start_time, first_start_time, second_end_time, second_content, first_content, out, done, "yes")
		if done:
			newid += 1
			second_sub_list = second_sub_list[1:]
			continue
		
		# 8) 3 of first sub matched against 1 of second sub is less than 1.25s
		if len(first_sub_list) > 2:
			first_end_time_ = first_sub_list[2][0][1]
			# TODO consider adding " - "
			first_content_ = first_content + " " + first_sub_list[1][0][2] + " " + first_sub_list[2][0][2]
			out, done, second_sub_list = endtime_diff(1.25, newid, second_sub_list, first_start_time, second_start_time, first_end_time_, second_end_time, first_content_, second_content, out, done)
			if done:
				newid += 1
				first_sub_list = first_sub_list[3:]
				continue
		
		# 9) 3 of second sub matched against 1 of first sub is less than 1.25s
		if len(second_sub_list) > 2:
			second_end_time_ = second_sub_list[2][0][1]
			# TODO consider adding " - "
			second_content_ = second_content + " " + second_sub_list[1][0][2] + " " + second_sub_list[2][0][2]
			out, done, first_sub_list = endtime_diff(1.25, newid, first_sub_list, second_start_time, first_start_time, second_end_time_, first_end_time, second_content_, first_content, out, done, "yes")
			if done:
				newid += 1
				second_sub_list = second_sub_list[3:]
				continue
		
		# 10) difference between end times is less than 2s
		out, done, second_sub_list = endtime_diff(2, newid, second_sub_list, first_start_time, second_start_time, first_end_time, second_end_time, first_content, second_content, out, done)
		if done:
			newid += 1
			first_sub_list = first_sub_list[1:]
			continue
		
		# 11) adjacent merged sub differs by less than 2s
		out, done, second_sub_list = merged_endtime_diff(2, newid, second_sub_list, first_start_time, second_start_time, first_end_time, first_content, second_content, out, done)
		if done:
			newid += 1
			first_sub_list = first_sub_list[1:]
			continue
		
		# 12) 4 of first sub matched against 1 of second sub is less than 1.25s
		if len(first_sub_list) > 3:
			first_end_time_ = first_sub_list[3][0][1]
			# TODO consider adding " - "
			first_content_ = first_content + " " + first_sub_list[1][0][2] + " " + first_sub_list[2][0][2] + " " + first_sub_list[3][0][2]
			out, done, second_sub_list = endtime_diff(1.25, newid, second_sub_list, first_start_time, second_start_time, first_end_time_, second_end_time, first_content_, second_content, out, done)
			if done:
				newid += 1
				first_sub_list = first_sub_list[4:]
				continue
		
		# 13) 4 of second sub matched against 1 of first sub is less than 1.25s
		if len(first_sub_list) > 3:
			second_end_time_ = second_sub_list[3][0][1]
			# TODO consider adding " - "
			second_content_ = second_content + " " + second_sub_list[1][0][2] + " " + second_sub_list[2][0][2] + " " + second_sub_list[3][0][2]
			out, done, first_sub_list = endtime_diff(1.25, newid, first_sub_list, second_start_time, first_start_time, second_end_time_, first_end_time, second_content_, first_content, out, done, "yes")
			if done:
				newid += 1
				second_sub_list = second_sub_list[4:]
				continue
		
		# 14) difference between end times is less than 2.5s
		out, done, second_sub_list = endtime_diff(2.5, newid, second_sub_list, first_start_time, second_start_time, first_end_time, second_end_time, first_content, second_content, out, done)
		if done:
			newid += 1
			first_sub_list = first_sub_list[1:]
			continue
		
		# 15) adjacent merged sub differs by less than 2.5s
		out, done, second_sub_list = merged_endtime_diff(2.5, newid, second_sub_list, first_start_time, second_start_time, first_end_time, first_content, second_content, out, done)
		if done:
			newid += 1
			first_sub_list = first_sub_list[1:]
			continue
		
		# 16) adjacent merged sub against adjacent merged sub by less than 2s
		if len(first_sub_list) > 1:
			first_end_time_ = first_sub_list[1][0][1]
			# TODO consider adding " - "
			first_content_ = first_content + " " + first_sub_list[1][0][2]
			out, done, second_sub_list = merged_endtime_diff(2, newid, second_sub_list, first_start_time, second_start_time, first_end_time_, first_content_, second_content, out, done)
			if done:
				newid += 1
				first_sub_list = first_sub_list[2:]
				continue
		
		# 17) REVERSED adjacent merged sub differs by less than 2s
		out, done, first_sub_list = merged_endtime_diff(2, newid, first_sub_list, second_start_time, first_start_time, second_end_time, second_content, first_content, out, done, "yes")
		if done:
			newid += 1
			second_sub_list = second_sub_list[1:]
			continue
		
		# 18) REVERSED adjacent merged sub differs by less than 2.5s
		out, done, first_sub_list = merged_endtime_diff(2.5, newid, first_sub_list, second_start_time, first_start_time, second_end_time, second_content, first_content, out, done, "yes")
		if done:
			newid += 1
			second_sub_list = second_sub_list[1:]
			continue
		
		# 19) adjacent merged sub differs by less than 2.75s
		out, done, second_sub_list = merged_endtime_diff(2.75, newid, second_sub_list, first_start_time, second_start_time, first_end_time, first_content, second_content, out, done)
		if done:
			newid += 1
			first_sub_list = first_sub_list[1:]
			continue
		
		# 20) REVERSED adjacent merged sub differs by less than 2.75s
		out, done, first_sub_list = merged_endtime_diff(2.75, newid, first_sub_list, second_start_time, first_start_time, second_end_time, second_content, first_content, out, done, "yes")
		if done:
			newid += 1
			second_sub_list = second_sub_list[1:]
			continue
		
		# 21) 4 of first sub matched against 1 of second sub is less than 1.5s
		if len(first_sub_list) > 3:
			first_end_time_ = first_sub_list[3][0][1]
			# TODO consider adding " - "
			first_content_ = first_content + " " + first_sub_list[1][0][2] + " " + first_sub_list[2][0][2] + " " + first_sub_list[3][0][2]
			out, done, second_sub_list = endtime_diff(1.5, newid, second_sub_list, first_start_time, second_start_time, first_end_time_, second_end_time, first_content_, second_content, out, done)
			if done:
				newid += 1
				first_sub_list = first_sub_list[4:]
				continue
		
		# 22) 4 of second sub matched against 1 of first sub is less than 1.5s
		if len(first_sub_list) > 3:
			second_end_time_ = second_sub_list[3][0][1]
			# TODO consider adding " - "
			second_content_ = second_content + " " + second_sub_list[1][0][2] + " " + second_sub_list[2][0][2] + " " + second_sub_list[3][0][2]
			out, done, first_sub_list = endtime_diff(1.5, newid, first_sub_list, second_start_time, first_start_time, second_end_time_, first_end_time, second_content_, first_content, out, done, "yes")
			if done:
				newid += 1
				second_sub_list = second_sub_list[4:]
				continue
		
		# 23) difference between end times is less than 3.75s
		out, done, second_sub_list = endtime_diff(3.75, newid, second_sub_list, first_start_time, second_start_time, first_end_time, second_end_time, first_content, second_content, out, done)
		if done:
			newid += 1
			first_sub_list = first_sub_list[1:]
			continue
		
		# no match
		if not done:
			print(f"No good match for first sub: {key}")
			unmatched = ', '.join([x[1] for x in unmatched_second_sub])
			print(f"IDs of unmatched in second_sub: {unmatched}")
			# add to output text with no match
			out += str(newid) + "\n" + first_start_time.strftime(time_format) + " --> " + first_end_time.strftime(time_format) + "\n" + first_content + "\n\n"
			newid += 1
			return out
	
	unmatched = ', '.join([x[1] for x in unmatched_second_sub])
	print(f"IDs of unmatched in second_sub: {unmatched}")
	print(f"Not outputted in second_sub: {len(second_sub_list)}")
	print(f"Not outputted in first_sub: {len(first_sub_list)}")
	
	return out


# calculate the difference in total seconds between two timestamps
def dates2seconds_diff(first_date, second_date):
	first_seconds = (first_date-dt.datetime(1900,1,1)).total_seconds()
	second_seconds = (second_date-dt.datetime(1900,1,1)).total_seconds()
	return abs(second_seconds - first_seconds)


# function for difference between end times
def endtime_diff(gap, key, second_sub_list, first_start_time, second_start_time, first_end_time, second_end_time, first_content, second_content, out, done, reverse = "no"):
	if dates2seconds_diff(second_end_time, first_end_time) < gap:
		# choose longest interval
		start_time = first_start_time if first_start_time < second_start_time else second_start_time
		end_time = first_end_time if first_end_time > second_end_time else second_end_time
		# switch around order of subs if input is reversed
		# TO DO maybe add - between second_contents
		if reverse == "no":
			content = first_content + "\n" + second_content
		elif reverse == "yes":
			content = second_content + "\n" + first_content
		else:
			print("Parameter issue")
			sys.exit()
		# add to output with match
		out += str(key) + "\n" + start_time.strftime(time_format) + " --> " + end_time.strftime(time_format) + "\n" + content + "\n\n"
		done = "yes"
		# remove ouputted sub from second_sub_list
		second_sub_list = second_sub_list[1:]
	return out, done, second_sub_list


# function for seeing if merging two from second_sub gives a match
def merged_endtime_diff(gap, key, second_sub_list, first_start_time, second_start_time, first_end_time, first_content, second_content, out, done, reverse = "no"):
	if len(second_sub_list) > 1:
		second_start_time_ = second_sub_list[1][0][0]
		second_end_time_ = second_sub_list[1][0][1]
		second_content_ = second_sub_list[1][0][2]
		if dates2seconds_diff(second_end_time_, first_end_time) < gap and second_start_time_ < first_end_time:
			# choose longest interval
			start_time = first_start_time if first_start_time < second_start_time else second_start_time
			end_time = first_end_time if first_end_time > second_end_time_ else second_end_time_
			# switch around order of subs if input is reversed
			# TO DO maybe add - between second_contents
			if reverse == "no":
				content = first_content + "\n" + second_content + " " + second_content_
			elif reverse == "yes":
				content = second_content + " " + second_content_ + "\n" + first_content
			else:
				print("Parameter issue")
				sys.exit()
			# add to output with merged match
			out += str(key) + "\n" + start_time.strftime(time_format) + " --> " + end_time.strftime(time_format) + "\n" + content + "\n\n"
			done = "yes"
			# remove ouputted sub from second_sub_list
			second_sub_list = second_sub_list[2:]
	return out, done, second_sub_list


# remove overlap from subs while making second sub to repeat if it's blank
def unoverlap(text):
	lines = text.split("\n")
	# initialise
	prevline = "blank"
	subs_dict = {}
	prev_id, prev_start_time, prev_end_time, prev_content = [""]*4
	
	# loop through text line by line
	for count, line in enumerate(lines):
		line = line.strip()
		
		# line is subtitle number so start new block
		if line.isnumeric() and prevline == "blank":
			id = line
			prevline = "id"
		# line is time stamp
		elif " --> " in line and prevline == "id":
			start_time, end_time = line.split(" --> ")
			# parse the timestamps
			start_time = datetime.strptime(start_time, time_format)
			end_time = datetime.strptime(end_time, time_format)
			prevline = "time"
		# line is first language text
		elif line and prevline == "time":
			first_content = line
			prevline = "first_content"
		# line is second language text
		elif line and prevline == "first_content":
			second_content = line
			prevline = "second_content"
		# line is blank so start new block
		elif not line:
			if prevline == "first_content":
				second_content = ""
			# add to all block's data to dict
			if prev_id not in subs_dict:
				# if times overlap reduce previous endtime
				if prev_end_time and count != len(lines) - 1 and start_time < prev_end_time:
					prev_end_time = start_time
					# if second language content is empty here then repeat from previous if previous is content from first sub
					if second_content == "" and first_content.endswith("{{1}}"):
						second_content = prev_second_content
				# add previous sub
				if prev_id:
					subs_dict[prev_id] = (prev_start_time, prev_end_time, prev_first_content, prev_second_content)
				# reassign prev objects
				prev_id = id
				prev_start_time = start_time
				prev_end_time = end_time
				prev_first_content = first_content
				prev_second_content = second_content
			else:
				print(f"ID used a second time on line {count}. Exited early")
				sys.exit()
			content = ""
			prevline = "blank"
		# unknown
		else:
			print(prevline)
			print(f"Issue on line {count}. Exited early")
	#	# if end of lines add final sub
	#	if count + 1 == len(lines):
	#		subs_dict[prev_id] = (prev_start_time, prev_end_time, prev_first_content, prev_second_content)
		
	
	out = ""
	for key, value in subs_dict.items():
		start_time = value[0]
		end_time = value[1]
		content = value[2] + "\n" + value[3] if value[3] else value[2]
		# remove marker from content
		content = re.sub(r"\{\{[12]\}\}", "", content)
		out += str(key) + "\n" + start_time.strftime(time_format) + " --> " + end_time.strftime(time_format) + "\n" + content + "\n\n"
	
	return out


def main():
	global time_format
	
	# define time format
	time_format = "%H:%M:%S,%f"
	
	# read first subtitle file
#	first_sub_path = r"C:\Users\james\Documents\Python\merge_subtitles\subs\idiots_eng.srt"
	first_sub_path = r"C:\Users\james\Documents\Python\merge_subtitles\subs\bohemian_life_eng.srt"
	with open(first_sub_path, "r") as r:
		first_sub = r.readlines()
	# add blank line to end just in case there isn't one
	if first_sub[-1] not in ["\r\n", "\n", "\r"]:
		first_sub += ["\n"]
	
	# read second subtitle file
#	second_sub_path = r"C:\Users\james\Documents\Python\merge_subtitles\subs\idiots_chn.srt"
	second_sub_path = r"C:\Users\james\Documents\Python\merge_subtitles\subs\bohemian_life_chn.srt"
	with open(second_sub_path, "r") as r:
		second_sub = r.readlines()
	# add blank line to end just in case there isn't one
	if second_sub[-1] not in ["\r\n", "\n", "\r"]:
		second_sub += ["\n"]
	
	# this will be the primary sub
	first_sub = parse_subs(first_sub, "first")
	# this will be the secondary sub
	second_sub = parse_subs(second_sub, "second")
	
	out = merge_subs(first_sub, second_sub)
	
	out = unoverlap(out)
	
	with open("merged_subs.srt", "w") as w:
		w.write(out)
	


if __name__ == "__main__":
    main()



