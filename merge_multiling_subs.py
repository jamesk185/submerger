
import re
from datetime import datetime
import sys

def parse_subs(text):
	# initialise
	prevline = "blank"
	content = ""
	subs_dict = {}
	
	# define time format
	time_format = "%H:%M:%S,%f"
	
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
				subs_dict[id] = (start_time, end_time, content)
			else:
				print(f"ID used a second time on line {count}. Exited early")
				sys.exit()
			content = ""
			prevline = "blank"
		# unknown
		else:
			print(f"Issue on line {count}. Exited early")
			sys.exit()


def main():
	
	# read first subtitle file
	first_sub_path = r"C:\Users\james\Videos\Movies\to_see\The_Bohemian_Life_(1992)_[1080p]\La.Vie.de.Boheme.1990.Criterion.1080p.BluRay.x265.HEVC.AAC-SARTRE.srt"
	with open(first_sub_path, "r") as r:
		first_sub = r.readlines()
	
	# read second subtitle file
	second_sub_path = r"C:\Users\james\Videos\Movies\to_see\The_Bohemian_Life_(1992)_[1080p]\[zmk.pw]The.Bohemian.Life.1992.1080p.BluRay.x264.AAC-[YTS.MX].srt"
	with open(second_sub_path, "r") as r:
		second_sub = r.readlines()
	
	parse_subs(first_sub)
	
	





if __name__ == "__main__":
    main()



