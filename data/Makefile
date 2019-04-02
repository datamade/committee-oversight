SHELL := /bin/bash

.PHONY : all clean
.INTERMEDIATE : processed/house.csv processed/senate.csv

all : final/house.csv final/house_committees.csv final/senate.csv	\
			final/senate_committees.csv

clean :
	rm -rf processed/*
	rm -rf final/*

processed/house.xlsx : raw/House_AllHearings.xlsx
	python get_urls.py 4 $^ $@

final/house.csv : processed/house.xlsx
	in2csv --sheet "Hearings" -S $^ | csvsort | uniq > $@

final/house_committees.csv : raw/House_AllHearings.xlsx
	in2csv --sheet "Key" -S $^ | csvcut -c 1,2 | sed '1s/.*/code,name/' > $@

processed/senate.xlsx : raw/Senate_AllHearings.xlsx
	python get_urls.py 3 $^ $@

final/senate.csv : processed/senate.xlsx
	in2csv --sheet "Hearings" -S $^ | csvsort | uniq > $@

final/senate_committees.csv : raw/Senate_AllHearings.xlsx
	in2csv --sheet "Key" -S $^ | csvcut -c 1,2 | sed '1s/.*/code,name/' > $@
