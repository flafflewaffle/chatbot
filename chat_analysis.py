import json
import os
import operator
import collections
import arrow
import emoji

class MessageReader:
    def __init__(self, stop_words_file, threshold, names=[], skip=[]):
        self.stop_words = []
        self.read_stop_words(stop_words_file)

        self.total_no_messages = 0
        self.vocabulary_size = 0
        self.bigram_phrases = 0
        self.trigram_phrases = 0
        self.threshold = threshold

        self.names = names
        self.skip = [self.tokenise(w) for w in skip]

        self.start_date = None
        self.end_date = None
        self.updated = arrow.utcnow()

        self.messages_per_person = {}
        self.total_term_frequency = {}
        self.term_frequency_names = {}
        self.bigram_total_term_frequency = {}
        self.bigram_term_frequency_names = {}
        self.trigram_total_term_frequency = {}
        self.trigram_term_frequency_names = {}

    # Read Stop Words
    def read_stop_words(self, stop_words_file):
        with open(stop_words_file, 'r') as f:
            print('Reading Stop Words')
            for line in f:
                for word in line.split():
                    self.stop_words.append(word.lower())

    # Retrieve the alphanumeric characters in lowercase
    def tokenise(self, word):
        return ''.join(ch for ch in word.lower() if ch.isalnum() or ch in emoji.UNICODE_EMOJI)

    # Reads all the messages in a directory
    def read_all_messages(self, message_dir, json=True):
        if os.path.isdir(message_dir):
            message_files = os.listdir(message_dir)
        else:
            print("Invalid directory provided: {}".format(message_dir))
            pass
        for message_file in message_files:
            file = '{}/{}'.format(message_dir, message_file)
            if not message_file.startswith('.') and os.path.isfile(file):
                print('Reading ',file)
                if json:
                    self.read_messages_json(file)
                else:
                    self.read_messages_txt(file)
            else:
                print("Invalid file provided: {}".format(file))
                pass

    # Reads a json file and saves the messages in a dictionary
    def read_json(self, filename):
        with open(filename) as json_file:
            messages = json.load(json_file)
        return messages

    #TODO: Add list of dates 
    # Reads and analyses the frequencies of messages (provided a json file)
    def read_messages_json(self, message_file):
        messages_json = self.read_json(message_file)
        print('Retrieving Names')
        participants = messages_json["participants"]
        self.names = [name for participant in participants for (key,name) in participant.items()]
        print('Reading Messages For, ', self.names)

        for name in self.names:
            if(name not in self.messages_per_person):
                self.messages_per_person[name] = 0

        messages = messages_json["messages"]
        for message in messages:
            date = arrow.get(message["timestamp_ms"]/1000)
            if self.start_date is not None: 
                if date < self.start_date:
                    self.start_date = date
            else:
                self.start_date = date
            if self.end_date is not None: 
                if date > self.end_date:
                    self.end_date = date
            else:
                self.end_date = date
            sender_name = message["sender_name"]
            if "content" in message:
                content = message["content"]

                # Message counts
                self.total_no_messages += 1
                self.messages_per_person[sender_name] += 1

                split_content = content.split()
                self.analyse_content(split_content, sender_name)
    
    # Reads and analyses the frequencies of messages (provided a txt file)
    def read_messages_txt(self, message_file):
        print('Reading Messages For, ', self.names)

        for name in self.names:
            if(name not in self.messages_per_person):
                self.messages_per_person[name] = 0

        with open(message_file, 'r') as f_read:
            for line in f_read:
                split_content = line.split()
                if(len(split_content)==0):
                    continue
                if('Messages to this chat and calls are now secured with end-to-end encryption. Tap for more info.' in line):
                    continue
                # Date and name
                date = split_content[0]
                if('/' in date and (date[0:2].isnumeric() or date[1:3].isnumeric())):
                    if(':' in line):
                        if(split_content[2] != '-'):
                            sender_name = split_content[2]
                            split_content = split_content[3:]
                            if(sender_name[-1] == ':'):
                                sender_name = sender_name[:-1]
                        else:
                            sender_name = split_content[3]
                            split_content = split_content[4:]
                            if(sender_name[-1] == ':'):
                                sender_name = sender_name[:-1]

                # Message counts
                self.total_no_messages += 1
                self.messages_per_person[sender_name] += 1

                self.analyse_content(split_content, sender_name)

    # Analyses the frequencies of terms, bigrams and trigrams given a list of words
    def analyse_content(self, split_content, sender_name):
        # Single word frequency analysis
        for word in split_content:
            term = self.tokenise(word)
            if(len(term) > 0 and term not in self.stop_words and term not in self.skip):
                if (term not in self.total_term_frequency):
                    self.total_term_frequency[term] = 0
                    self.vocabulary_size += 1
                    self.term_frequency_names[term] = {}
                    for name in self.names:
                        self.term_frequency_names[term][name] = 0
                self.total_term_frequency[term] += 1
                self.term_frequency_names[term][sender_name] += 1

        # Bigram frequency analysis
        # Ignores frequencies of less than 4 (nonsensical phrases)
        i = 0
        while(i < len(split_content)-2):
            bigram = ' '.join([self.tokenise(w) for w in split_content[i:i+2] if self.tokenise(w) not in self.skip])
            i += 1
            if(len(bigram) > 0):
                if (bigram not in self.bigram_total_term_frequency):
                    self.bigram_total_term_frequency[bigram] = 0
                    self.bigram_term_frequency_names[bigram] = {}
                    for name in self.names:
                        self.bigram_term_frequency_names[bigram][name] = 0
                self.bigram_total_term_frequency[bigram] += 1
                if(self.bigram_total_term_frequency[bigram] >= self.threshold):
                    self.bigram_phrases += 1
                self.bigram_term_frequency_names[bigram][sender_name] += 1

        # Trigram frequency analysis
        # Ignores frequencies of less than 4 (nonsensical phrases)
        i = 0
        while(i < len(split_content)-3):
            trigram = ' '.join([self.tokenise(w) for w in split_content[i:i+3] if self.tokenise(w) not in self.skip])
            i += 1
            if(len(trigram) > 0):
                if (trigram not in self.trigram_total_term_frequency):
                    self.trigram_total_term_frequency[trigram] = 0
                    self.trigram_term_frequency_names[trigram] = {}
                    for name in self.names:
                        self.trigram_term_frequency_names[trigram][name] = 0
                self.trigram_total_term_frequency[trigram] += 1
                if(self.trigram_total_term_frequency[trigram] >= self.threshold):
                    self.trigram_phrases += 1
                self.trigram_term_frequency_names[trigram][sender_name] += 1


    # Writes out the message stats in json files
    def write_stat_json_files(self, friend):
        dir_name = './{}_stats'.format(friend)
        if not os.path.isdir(dir_name):
            os.mkdir(dir_name)
        
        json_file= open('{}/{}_stats.json'.format(dir_name,friend))
        json.dump(self.total_term_frequency, json_file)
        json_file.close()

        json_file= open('{}/{}_bigram_stats.json'.format(dir_name,friend))
        json.dump(self.bigram_total_term_frequency, json_file)
        json_file.close()

        json_file= open('{}/{}_trigram_stats.json'.format(dir_name,friend))
        json.dump(self.trigram_total_term_frequency, json_file)
        json_file.close()

    # Writes out the message stats in a readable text format
    def write_stat_text_files(self, friend):
        dir_name = './{}_stats'.format(friend)
        if not os.path.isdir(dir_name):
            os.mkdir(dir_name)

        # Write Metadata File
        with open('{}/{}_metadata.txt'.format(dir_name, friend), 'w') as f_write:
            f_write.write(str('Last Updated: %s' % self.updated.format('YYYY-MM-DD HH:mm:ss')))
            f_write.write('\n')

            f_write.write(str('Vocabulary Size: %d' % self.vocabulary_size))
            f_write.write('\n')

            f_write.write(str('Total Number of Messages: %d' % self.total_no_messages))
            f_write.write('\n')

            f_write.write(str('Total Number of Messages: %d' % self.total_no_messages))
            f_write.write('\n')

            for name in self.names:
                f_write.write(str('%s: %d' % (name, self.messages_per_person[name])))
                f_write.write('\n')

            f_write.write(str('Number of Bigram Phrases: %d' % self.bigram_phrases))
            f_write.write('\n')

            f_write.write(str('Number of Trigram Phrases: %d' % self.trigram_phrases))
            f_write.write('\n')

            if self.start_date is not None: 
                f_write.write(str('Start Date: %s' % self.start_date.format('YYYY-MM-DD')))
                f_write.write('\n')

            if self.end_date is not None:
                f_write.write(str('End Date: %s' % self.end_date.format('YYYY-MM-DD')))
                f_write.write('\n')

        # Write Single Term Frequency file
        with open('{}/{}_stats.txt'.format(dir_name, friend), 'w') as f_write:
            f_write.write(str('Vocabulary Size: %d' % self.vocabulary_size))
            f_write.write('\n')

            f_write.write(str('Total Number of Messages: %d' % self.total_no_messages))
            f_write.write('\n')

            for name in self.names:
                f_write.write(str('%s: %d' % (name, self.messages_per_person[name])))
                f_write.write('\n')

            f_write.write('\n')
            f_write.write('WORD FREQUENCIES')
            f_write.write('\n\n')

            sort_by_freq = sorted(self.total_term_frequency.items(),key=operator.itemgetter(1),reverse=True)
            sorted_term_frequency = collections.OrderedDict(sort_by_freq)
            for word, frequency in sorted_term_frequency.items():
                f_write.write(str('%s: %s'% (word.encode('utf8'),frequency)))
                f_write.write('\n')
                for name in self.names:
                    f_write.write('\t')
                    f_write.write(str('%s: %s'% (name,self.term_frequency_names[word][name])))
                    f_write.write('\n')

        # Write Bigram Frequency file
        with open('{}/{}_bigram_stats.txt'.format(dir_name, friend), 'w') as f_write:
            f_write.write('BIGRAM PHRASE FREQUENCIES')
            f_write.write('\n\n')
            f_write.write(str('Number of Bigram Phrases: %d' % self.bigram_phrases))
            f_write.write('\n')

            sort_by_freq = sorted(self.bigram_total_term_frequency.items(),key=operator.itemgetter(1),reverse=True)
            sorted_bigram_term_frequency = collections.OrderedDict(sort_by_freq)
            for word, frequency in sorted_bigram_term_frequency.items():
                if(frequency >= self.threshold):
                    f_write.write(str('%s: %s'% (word.encode('utf8'),frequency)))
                    f_write.write('\n')
                    for name in self.names:
                        f_write.write('\t')
                        f_write.write(str('%s: %s'% (name,self.bigram_term_frequency_names[word][name])))
                        f_write.write('\n')

        # Write Trigram Frequency file
        with open('{}/{}_trigram_stats.txt'.format(dir_name, friend), 'w') as f_write:
            f_write.write('TRIGRAM PHRASE FREQUENCIES')
            f_write.write('\n\n')
            f_write.write(str('Number of Trigram Phrases: %d' % self.trigram_phrases))
            f_write.write('\n')

            sort_by_freq = sorted(self.trigram_total_term_frequency.items(),key=operator.itemgetter(1),reverse=True)
            sorted_trigram_term_frequency = collections.OrderedDict(sort_by_freq)
            for word, frequency in sorted_trigram_term_frequency.items():
                if(frequency >= self.threshold):
                    f_write.write(str('%s: %s'% (word.encode('utf8'),frequency)))
                    f_write.write('\n')
                    for name in self.names:
                        f_write.write('\t')
                        f_write.write(str('%s: %s'% (name,self.trigram_term_frequency_names[word][name])))
                        f_write.write('\n')