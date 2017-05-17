# !/usr/bin/env python
# -*- coding: utf-8 -*-

##############################################################################
#
# PyKeylogger: TTT for Linux and Windows
# Copyright (C) 2016 Roxana Lafuente <roxana.lafuente@gmail.com>
#                    Miguel Lemos <miguelemosreverte@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import subprocess
import os

def filterTER (lines):
    result = ''
    lines = lines.splitlines()
    for line in lines:
        if "Total TER:" in line:
            result += line.replace("Total TER:","")[0:6]
    return result + "\n"

def filterBLEU (line, BLEU_type):
    if BLEU_type == "BLEU":      line = line.split(',', 1)[0]
    if BLEU_type == "BLEU2GRAM": line = line.split(',', 1)[1].split('/')[0]
    if BLEU_type == "BLEU3GRAM": line = line.split(',', 1)[1].split('/')[1]
    if BLEU_type == "BLEU4GRAM": line = line.split(',', 1)[1].split('/')[2]
    line = line.replace('\n','').replace('\r', '')
    return line

def filter_output(proccess,method):
    out, err = proccess.communicate()
    final_text = ""
    if not err :
        final_text = out
    else: final_text = err
    if method == "HTER": final_text = filterTER(final_text)
    if method == "GTM": final_text = filterGTM(final_text)
    if method == "PER" or method == "WER": pass
    try:
        final_text = str(round(float(final_text), 3))
    except ValueError:
        pass
    return final_text


def evaluate(checkbox_indexes, hypothesis, reference, all_cached_results, file_hash):
    cached_results = all_cached_results[file_hash]
    checkbox_indexes_constants = ["WER","PER","HTER", "BLEU","BLEU2GRAM","BLEU3GRAM","BLEU4GRAM"]
    DIRECTORY = "/home/moses/Downloads/api/TTT/evaluation_scripts/"
    TER_DIRECTORY = DIRECTORY + "java_ter_060428 TERtest"
    EXEC_PERL = "perl "
    EXEC_JAVA = "java "

    evaluation_scripts_commands = {}
    evaluation_scripts_commands["WER"] = EXEC_PERL + DIRECTORY +  "WER" + ".pl" + " -t " + hypothesis + " -r " + reference
    evaluation_scripts_commands["PER"] = EXEC_PERL + DIRECTORY +  "PER" + ".pl" + " -t " + hypothesis + " -r " + reference
    evaluation_scripts_commands["HTER"] = EXEC_JAVA + "-cp " + TER_DIRECTORY + " " + hypothesis + " " + reference
    evaluation_scripts_commands["BLEU"] = EXEC_PERL + DIRECTORY + "BLEU.pl " + reference +" < " + hypothesis
    return_results = ""
    checkbox_index = 0
    BLEU_cached_results = ""
    for checkbox in checkbox_indexes:
        if checkbox:
            key = checkbox_indexes_constants[checkbox_index]
            if key in cached_results: return_results += cached_results[key]
            else:

                if "BLEU" in checkbox_indexes_constants[checkbox_index] and BLEU_cached_results == "":
                    command = evaluation_scripts_commands["BLEU"]
                    proc = subprocess.Popen(command, shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    while True:
                      line = proc.stdout.readline()
                      if line != '':BLEU_cached_results += line
                      else: break

                if "BLEU" in checkbox_indexes_constants[checkbox_index]:
                    result = "\n" + checkbox_indexes_constants[checkbox_index] + "..... "\
                        + filterBLEU(BLEU_cached_results,checkbox_indexes_constants[checkbox_index])
                    return_results += result
                    cached_results[key] =  result

                else:
                    command = evaluation_scripts_commands[checkbox_indexes_constants[checkbox_index]]
                    proc = subprocess.Popen(command, shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    result = "\n" + checkbox_indexes_constants[checkbox_index] + "..... " + filter_output(proc,checkbox_indexes_constants[checkbox_index])
                    return_results += result
                    cached_results[key] =  result


        checkbox_index += 1
    all_cached_results[file_hash] = cached_results
    return return_results
