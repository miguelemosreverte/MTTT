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

from __future__ import print_function # In python 2.7
def install_and_import(package):
    import importlib
    try:
        importlib.import_module(package)
    except ImportError:
	try:
	        import pip
    	except ImportError:
		print ("no pip")
		os.system('python get_pip.py')
	finally:
		import pip
        pip.main(['install', package])
    finally:
        globals()[package] = importlib.import_module(package)

#os is one of the modules that I know comes with 2.7, no questions asked.
import os
#these other ones I a am not so sure of. Thus the install function.
install_and_import("subprocess")
install_and_import("sys")
install_and_import("time")
install_and_import("hashlib")
install_and_import("datetime")

from commands import *
from files_processing import *
from constants import moses_dir_fn, languages
from evaluation import evaluate


class TTT():


    def __init__(self):

        '''
        TTT uses MD5 based hashing of files content
        to create unique filenames to be used inside
        of a temporal folder.

        1-An example for it is the caching of evaluation results for a given pair of files,
        or
        2-the saving of untranslated text to be translated by Moses:
        Moses only accepts filenames, not text, as parameter input
        for machine translation.
        '''
        self.files_hashes_and_performed_evaluations_indices = {}

        self.moses_dir = "/home/moses/mosesdecoder"
        self.temp_dir = "/home/moses/temp/"
        self.lm_dir_not_persistent = "/home/moses/language_models/"
        self.lm_dir_persistent = "/var/lib/moses_api_backup/language_models/"

    def _prepare_corpus(self, language_model_name, source_lang, target_lang, training_source, training_target, language_model_text):
        """@brief     Runs moses truecaser, tokenizer and cleaner."""

        output_directory = self.lm_dir_persistent + language_model_name
        training_source_filepath = output_directory + '/' + 'training_source'
        training_target_filepath = output_directory + '/' + 'training_target'
        language_model_filepath = output_directory + '/' + 'language_model_text'

        #the app will never let the users create the same language model twice
        #which guarantees that the following will always be needed:
        os.makedirs(output_directory)
        with open(language_model_filepath, "w") as f:
            f.write(language_model_text.encode('utf-8'))
        with open(training_source_filepath, "w") as f:
            f.write(training_source.encode('utf-8'))
        with open(training_target_filepath, "w") as f:
            f.write(training_target.encode('utf-8'))


        output = ""
        os.chdir(output_directory)
        cmds = []
        # 1) Tokenization
        # a) Target text
        target_tok = generate_input_tok_fn(target_lang,
                                                output_directory)
        cmds.append(get_tokenize_command(self.moses_dir,
                                         target_lang,
                                         training_target_filepath,
                                         target_tok))
        # b) Source text
        source_tok = generate_input_tok_fn(source_lang,
                                                output_directory)
        cmds.append(get_tokenize_command(self.moses_dir,
                                         source_lang,
                                         training_source_filepath,
                                         source_tok))
        # c) Language model
        lm_tok = generate_lm_tok_fn(output_directory)
        cmds.append(get_tokenize_command(self.moses_dir,
                                         source_lang,
                                         language_model_filepath,
                                         lm_tok))

        # 2) Truecaser training
        # a) Target text
        cmds.append(get_truecaser_train_command(self.moses_dir,
                                                output_directory,
                                                target_lang,
                                                target_tok))
        # b) Source text
        cmds.append(get_truecaser_train_command(self.moses_dir,
                                                output_directory,
                                                source_lang,
                                                source_tok))
        # c) Language model
        cmds.append(get_truecaser_train_command(self.moses_dir,
                                                output_directory,
                                                target_lang,
                                                lm_tok))

        # 3) Truecaser
        input_true = output_directory + "/input.true"
        # a) Target text
        target_true = generate_input_true_fn(target_lang,
                                                  output_directory)
        cmds.append(get_truecaser_command(self.moses_dir,
                                          output_directory,
                                          target_lang,
                                          target_tok,
                                          target_true))
        # b) Source text
        source_true = generate_input_true_fn(source_lang,
                                                  output_directory)
        cmds.append(get_truecaser_command(self.moses_dir,
                                          output_directory,
                                          source_lang,
                                          source_tok,
                                          source_true))
        # c) Language model
        lm_true = generate_lm_true_fn(output_directory)
        cmds.append(get_truecaser_command(self.moses_dir,
                                          output_directory,
                                          target_lang,
                                          target_tok, lm_true))

        # 4) Cleaner
        # a) Target text
        input_clean = generate_input_clean_fn(output_directory)
        source_clean = input_true + "." + source_lang
        target_clean = input_true + "." + target_lang
        cmds.append(get_cleaner_command(self.moses_dir,
                                        source_lang,
                                        target_lang,
                                        input_true,
                                        input_clean))

        # Start threads
        all_ok = True
        for cmd in cmds:
            output += "Running command: <code> <p style=\"background-color:LightGray;\">%s" % cmd + "</p> </code>"
            proc = subprocess.Popen([cmd],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    shell=True)
            all_ok = all_ok and (proc.wait() == 0)
            out, err = proc.communicate()
            if out or err:  output += "Output: %s<br>%s<br><br><br>" % (out, err)
            else:           output += "<br><br><br>"

        if all_ok:
            with open(output_directory + '/lm.ini', 'w') as f:
                f.write("source_lang:"+source_lang+"<br>")
                f.write("target_lang:"+target_lang+"<br>")
        return output

    def _train(self,language_model_name, source_lang, target_lang):

        output_directory = self.lm_dir_persistent + language_model_name
        output = ""
        if output_directory is not None:
            cmds = []
            output = "Log:<br><br>"
            # Train the language model.
            lm_arpa = generate_lm_fn(output_directory)
            print ("out:", lm_arpa, "<br>")
            cmds.append(get_lmtrain_command(self.moses_dir,
                                            target_lang,
                                            output_directory + '/' + 'lm.true',
                                            lm_arpa))

            # Binarize arpa
            blm = generate_blm_fn(output_directory)
            print ("binarized out:", blm, "<br>")
            cmds.append(get_blmtrain_command(self.moses_dir,
                                             target_lang,
                                             lm_arpa,
                                             blm))


            # Train the translation model.
            out_file = generate_tm_fn(output_directory)
            cmds.append(get_tmtrain_command(self.moses_dir,
                                             source_lang,
                                            target_lang,
                                            blm,
                                            output_directory + '/' + 'input.clean',
                                            output_directory))

            # TODO!
            # Binarize phase-table.gz
            # Binarize reordering-table.wbe-msd-bidirectional-fe.gz
            # Change PhraseDictionaryMemory to PhraseDictionaryCompact
            # Set the path of the PhraseDictionary feature to point to $HOME/working/binarised-model/phrase-table.minphr
            # Set the path of the LexicalReordering feature to point to $HOME/working/binarised-model/reordering-table

            for cmd in cmds:
                # use Popen for non-blocking
                output += cmd + "\n"
                proc = subprocess.Popen([cmd],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True)
                proc.wait()
                (out, err) = proc.communicate()
                if out != "":
                    output += out
                elif err != "":
                    output += err

            # Adding output from training.out
            training = output_directory + "/training.out"
            try:
                with open(training, "r") as f:
                   output += "\n" + f.read()
            except IOError:pass

            # Set output to the output label.
        else:
            output = "ERROR: Please go to the first tab and complete the process."
        return output

    def _machine_translation(self, language_model_name, text):
        file_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        mt_in = self.temp_dir + file_hash
        with open(mt_in, "w") as f:
            f.write(text.encode('utf-8'))

        #Todo see if this os.chdir can be removed
        os.chdir(self.lm_dir_persistent)
        base=os.path.basename(mt_in)
        mt_out = os.path.dirname(mt_in) +  "/" + os.path.splitext(base)[0] + "_translated" + os.path.splitext(base)[1]
        output = "Running decoder....<br><br>"
        # Run the decoder.
        cmd = get_test_command(self.moses_dir,
                                  self.lm_dir_persistent +  language_model_name + "/train/model/moses.ini",
                                   mt_in,
                                   mt_out)
        # use Popen for non-blocking
        proc = subprocess.Popen([cmd],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    shell=True)
        (out, err) = proc.communicate()
        f = open(mt_out, 'r')
        mt_result = f.read()
        if mt_result == "":
                if out != "":
                    output += out
                elif err != "":
                    output += err
        else:
                output += "Best translation: " + mt_result

        f.close()
        return output

    def get_available_languages(self):
        return languages

    def evaluate(self, checkbox_indexes, test, reference):
        file_hash = hashlib.md5(test + reference).hexdigest()
        temp_dir = self.temp_dir + file_hash
        test_path = temp_dir + "/test.txt"
        reference_path = temp_dir + "/reference.txt"

        #the hash resulted from the sum of the two files guarantees
        #that only once will the combinations of them exist
        #and so only once is neccesary to create a temporal directory
        try:
            os.stat(temp_dir)
        except:
            os.mkdir(temp_dir)
            with open(test_path, "w") as f:
                f.write(test)
            with open(reference_path, "w") as f:
                f.write(reference)

        now = datetime.datetime.now()
        if not hasattr(self, 'current_hour'): current_hour = now.hour
        #every hour the cached results are reset
        if (now.hour != current_hour):
            self.files_hashes_and_performed_evaluations_indices.clear()
            current_hour = now.hour

        #finally a dictionary from the file_hashes to the result of the
        #previously performed evaluation scripts is stored, by the hour
        if (file_hash not in self.files_hashes_and_performed_evaluations_indices):
            self.files_hashes_and_performed_evaluations_indices[file_hash] = {}
        return evaluate(checkbox_indexes, test_path, reference_path, self.files_hashes_and_performed_evaluations_indices, file_hash)
