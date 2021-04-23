# ==================================================================================
# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ==================================================================================
#
# srtUtils.py
# by: Rob Dachowski
# For questions or feedback, please contact robdac@amazon.com
# 
# Purpose: The program provides a number of utility functions for creating SubRip Subtitle files (.SRT)
#
# Change Log:
#          6/29/2018: Initial version
#
# ==================================================================================

import json
import boto3
import re
import codecs
import time
import math
from audioUtils import *
from pydub import AudioSegment



# ==================================================================================
# Function: newPhrase
# Purpose: simply create a phrase tuple
# Parameters: 
#                 None
# ==================================================================================
def newPhrase():
    return { 'start_time': '', 'end_time': '', 'words' : [] ,
             'start_second': 0, 'end_second': 0, 'punctuation': ''}


        
# ==================================================================================
# Function: getTimeCode
# Purpose: Format and return a string that contains the converted number of seconds into SRT format
# Parameters: 
#                 seconds - the duration in seconds to convert to HH:MM:SS,mmm 
# ==================================================================================    
        # Format and return a string that contains the converted number of seconds into SRT format
def getTimeCode(seconds):
# ....t_hund = int(seconds % 1 * 1000)
# ....t_seconds = int( seconds )
# ....t_secs = ((float( t_seconds) / 60) % 1) * 60
# ....t_mins = int( t_seconds / 60 )
# ....return str( "%02d:%02d:%02d,%03d" % (00, t_mins, int(t_secs), t_hund ))
    (frac, whole) = math.modf(seconds)
    frac = frac * 1000
    return str('%s,%03d' % (time.strftime('%H:%M:%S',time.gmtime(whole)), frac))
        

# ==================================================================================
# Function: writeTranscriptToSRT
# Purpose: Function to get the phrases from the transcript and write it out to an SRT file
# Parameters: 
#                 transcript - the JSON output from Amazon Transcribe
#                 sourceLangCode - the language code for the original content (e.g. English = "EN")
#                 srtFileName - the name of the SRT file (e.g. "mySRT.SRT")
# ==================================================================================    
def writeTranscriptToSRT( transcript, sourceLangCode, srtFileName ):
        # Write the SRT file for the original language
        print( "==> Creating SRT from transcript")
        phrases = getPhrasesFromTranscript( transcript )
        writeSRT( phrases, srtFileName )
        

    

# ==================================================================================
# Function: writeTranscriptToSRT
# Purpose: Based on the JSON transcript provided by Amazon Transcribe, get the phrases from the translation 
#          and write it out to an SRT file
# Parameters: 
#                 transcript - the JSON output from Amazon Transcribe
#                 sourceLangCode - the language code for the original content (e.g. English = "EN")
#                 targetLangCode - the language code for the translated content (e.g. Spanich = "ES")
#                 srtFileName - the name of the SRT file (e.g. "mySRT.SRT")
# ==================================================================================
def writeTranslationToSRT( transcript, sourceLangCode, targetLangCode, srtFileName, region ):
        # First get the translation
        print(( "\n\n==> Translating from " + sourceLangCode + " to " + targetLangCode ))
        ##translation = translateTranscript( transcript, sourceLangCode, targetLangCode, region )
        #print( "\n\n==> Translation: " + str(translation))
                
        # Now create phrases from the translation
        ##textToTranslate = str(translation["TranslatedText"])
        ##phrases = getPhrasesFromTranslation( textToTranslate, targetLangCode )
        #phrases = getTranslationFromPhrases( getPhrasesFromTranscript( transcript) , sourceLangCode, targetLangCode, region )
        #writeSRT( phrases, srtFileName )
        phrases = getMergedPhrases( getPhrasesFromTranscript( transcript) )
        #print(phrases)
        writeSRT( splitPhrases( phrases, sourceLangCode, targetLangCode, region), srtFileName )

# ==================================================================================
# Function: splitPhrases
# Purpose: split a long phrases into shorter phrases
# Parameters: 
#                 ophrases - phrases built by getTranslationFromPhrases
#                 sourceLangCode - the language code for the original content (e.g. English = "EN")
#                 targetLangCode - the language code for the translated content (e.g. Spanich = "ES")
#                 region - the AWS region in which to run the Translation (e.g. "us-east-1")
# ==================================================================================    
def splitPhrases( ophrases, sourceLangCode, targetLangCode, region):

        #set up some variables for the first pass
        phrases = []
        x = 0
        c = 0
        lineLengths = [5, 7, 9]
        phrase_startTime = 0
        phrase_endTime = 0
        translation = ''

        sound0 = AudioSegment.from_file("audio.mp3")


        for ophrase in ophrases:

            phrase = newPhrase()
            nPhrase = True
            phrase_startTime = ophrase["start_second"]
            phrase_endTime = ophrase["end_second"]
            translation = translateText( ' '.join(ophrase["words"]), sourceLangCode, targetLangCode, region)
            translated_txt = str(translation["TranslatedText"])
            words = translated_txt.split()
            countWords = len(words)
            audioDuration = phrase_endTime - phrase_startTime
            if countWords:
                secondPerWord = audioDuration / countWords
            #wordsPerLine = max( lineLengths, key = lambda x: countWords % x)
            wordsPerLine = 9
            seconds = wordsPerLine * secondPerWord
            c += 1
            audioFileName = "phraseAudio_" + str(c) + ".mp3"
            outFileName = "track-" + targetLangCode + ".mp3"
            #print(c)
            #print(ophrase)
            #print(words)
            createAudioTrackFromText( translated_txt, targetLangCode, region, audioFileName, audioDuration )
            sound0 = overlayAudio( sound0, audioFileName, phrase_startTime * 1000)
    
            for word in words:

                # if it is a new phrase, then get the start_time of the first phrase
                if nPhrase == True:
                    phrase["start_time"] = getTimeCode(phrase_startTime)
                    nPhrase = False

                # Append the words to the phrase...
                phrase["words"].append(word)
                x += 1
    
                # now add the phrase to the phrases, generate a new phrase, etc.
                if (x == wordsPerLine) or (x > 2 and word[-1] in ['.',',']) :
                    phrase["end_time"] = getTimeCode(min([phrase_startTime + x * secondPerWord,phrase_endTime]))
                    phrase_startTime += x * secondPerWord
                    #print(x,phrase)
                    phrases.append(phrase)
                    phrase = newPhrase()
                    nPhrase = True
                    x = 0

            if (len(phrase["words"]) > 0):
                if phrase["end_time"] == '':
                    phrase["end_time"] = getTimeCode( phrase_endTime )
                phrases.append(phrase)
                #print(phrase)

        print("\n==> Writing track: {:s}".format(outFileName))
        sound0.export(outFileName)

        return phrases


# ==================================================================================
# Function: splitPhrase
# Purpose: split a long phrase into shorter phrases
# Parameters: 
#                 ophrase - phrase built by getTranslationFromPhrases
#                 sourceLangCode - the language code for the original content (e.g. English = "EN")
#                 targetLangCode - the language code for the translated content (e.g. Spanich = "ES")
#                 region - the AWS region in which to run the Translation (e.g. "us-east-1")
# ==================================================================================    
def splitPhrase( ophrase, sourceLangCode, targetLangCode, region):

        #set up some variables for the first pass
        phrases = []
        phrase = newPhrase()
        nPhrase = True
        x = 0
        c = 0
        lineLengths = [ 7, 9]
        phrase_startTime = ophrase["start_second"]
        phrase_endTime = ophrase["end_second"]
        translation = translateText( ' '.join(ophrase["words"]), sourceLangCode, targetLangCode, region)
        translated_txt = str(translation["TranslatedText"])
        words = translated_txt.split()
        countWords = len(words)
        audioDuration = phrase_endTime - phrase_startTime
        secondPerWord = audioDuration / countWords
        wordsPerLine = max( lineLengths, key = lambda x: countWords % x)
        seconds = wordsPerLine * secondPerWord

        #createAudioTrackFromText( translated_txt, targetLangCode, audioFileName, audioDuration ):

        for word in words:

            # if it is a new phrase, then get the start_time of the first phrase
            if nPhrase == True:
                phrase["start_time"] = getTimeCode(phrase_startTime)
                nPhrase = False

            # Append the words to the phrase...
            phrase["words"].append(word)
            x += 1

            # now add the phrase to the phrases, generate a new phrase, etc.
            if x == wordsPerLine:
                phrase["end_time"] = getTimeCode(phrase_startTime + seconds)
                phrase_startTime += seconds
                phrases.append(phrase)
                phrase = newPhrase()
                nPhrase = True
                x = 0

        if (len(phrase["words"]) > 0):
            if phrase["end_time"] == '':
                phrase["end_time"] = getTimeCode( phrase_endTime )
            phrases.append(phrase)

        return phrases

# ==================================================================================
# Function: getMergedPhrases
# Purpose: Translate each phrase in phrases 
# Parameters: 
#                 ophrases - phrases built by getPhrasesFromTranscribe
# ==================================================================================    
def getMergedPhrases( ophrases ):

        #set up some variables for the first pass
        phrase =  newPhrase()
        phrases = []
        nPhrase = True
        c = 0

        print("==> Merging phrases...")

        for line in ophrases:

                # if it is a new phrase, then get the start_time of the first phrase
                if nPhrase == True:
                        phrase["start_time"] = line["start_time"]
                        phrase["start_second"] = line["start_second"]
                        nPhrase = False
                        c += 1
                                
                # Append the words to the phrase...
                phrase["words"].extend(line["words"])
                phrase["end_time"] = line["end_time"]
                phrase["end_second"] = line["end_second"]
                phrase["punctuation"] = line["punctuation"]
                
                # now add the phrase to the phrases, generate a new phrase, etc.
                if phrase["punctuation"] == '.':
                    #phrases.extend( splitPhrase(phrase, sourceLangCode, targetLangCode, region) )
                    phrases.append( phrase )
                    phrase = newPhrase()
                    nPhrase = True
                
        if (len(phrase["words"]) > 0):
                #phrases.extend( splitPhrase(phrase, sourceLangCode, targetLangCode, region) )
                phrases.append( phrase )

        return phrases

# ==================================================================================
# Function: getTranslationFromPhrases
# Purpose: Translate each phrase in phrases 
# Parameters: 
#                 ophrases - phrases built by getPhrasesFromTranscribe
#                 targetLangCode - the language code for the translated content (e.g. Spanich = "ES")
# ==================================================================================    
def getTranslationFromPhrases( ophrases, sourceLangCode, targetLangCode, region ):

        #set up some variables for the first pass
        phrase =  newPhrase()
        phrases = []
        nPhrase = True
        c = 0

        print("==> Creating translation from phrases...")

        for line in ophrases:

                # if it is a new phrase, then get the start_time of the first phrase
                if nPhrase == True:
                        phrase["start_time"] = line["start_time"]
                        phrase["start_second"] = line["start_second"]
                        nPhrase = False
                        c += 1
                                
                # Append the words to the phrase...
                phrase["words"].extend(line["words"])
                phrase["end_time"] = line["end_time"]
                phrase["end_second"] = line["end_second"]
                phrase["punctuation"] = line["punctuation"]
                
                # now add the phrase to the phrases, generate a new phrase, etc.
                if phrase["punctuation"] == '.':
                    phrases.extend( splitPhrase(phrase, sourceLangCode, targetLangCode, region) )
                    phrase = newPhrase()
                    nPhrase = True
                
        if (len(phrase["words"]) > 0):
                phrases.extend( splitPhrase(phrase, sourceLangCode, targetLangCode, region) )

        return phrases

# ==================================================================================
# Function: getPhrasesFromTranslation
# Purpose: Based on the JSON translation provided by Amazon Translate, get the phrases from the translation 
#          and write it out to an SRT file.  Note that since we are using a block of translated text rather than
#          a JSON structure with the timing for the start and end of each word as in the output of Transcribe,
#          we will need to calculate the start and end-time for each phrase
# Parameters: 
#                 translation - the JSON output from Amazon Translate
#                 targetLangCode - the language code for the translated content (e.g. Spanich = "ES")
# ==================================================================================    
def getPhrasesFromTranslation( translation, targetLangCode ):

        # Now create phrases from the translation
        words = translation.split()
        
        #print( words ) #debug statement
        
        #set up some variables for the first pass
        phrase =  newPhrase()
        phrases = []
        nPhrase = True
        x = 0
        c = 0
        seconds = 0

        print("==> Creating phrases from translation...")

        for word in words:

                # if it is a new phrase, then get the start_time of the first item
                if nPhrase == True:
                        phrase["start_time"] = getTimeCode( seconds )
                        nPhrase = False
                        c += 1
                                
                # Append the word to the phrase...
                phrase["words"].append(word)
                x += 1
                
                
                # now add the phrase to the phrases, generate a new phrase, etc.
                if x == 10:
                
                        # For Translations, we now need to calculate the end time for the phrase
                        psecs = getSecondsFromTranslation( getPhraseText( phrase), targetLangCode, "phraseAudio" + str(c) + ".mp3" ) 
                        seconds += psecs
                        phrase["end_time"] = getTimeCode( seconds )
                
                        #print c, phrase
                        phrases.append(phrase)
                        phrase = newPhrase()
                        nPhrase = True
                        #seconds += .001
                        x = 0
                        
                # This if statement is to address a defect in the SubtitleClip.   If the Subtitles end up being
                # a different duration than the content, MoviePy will sometimes fail with unexpected errors while
                # processing the subclip.   This is limiting it to something less than the total duration for our example
                # however, you may need to modify or eliminate this line depending on your content.
                #if c == 30:
                        #break
                        
        return phrases
        

# ==================================================================================
# Function: getPhrasesFromTranscript
# Purpose: Based on the JSON transcript provided by Amazon Transcribe, get the phrases from the translation 
#          and write it out to an SRT file
# Parameters: 
#                 transcript - the JSON output from Amazon Transcribe
# ==================================================================================
def getPhrasesFromTranscript( transcript ):

        # This function is intended to be called with the JSON structure output from the Transcribe service.  However,
        # if you only have the translation of the transcript, then you should call getPhrasesFromTranslation instead

        # Now create phrases from the translation
        ts = json.loads( transcript )
        items = ts['results']['items']
        #print( items )
        
        #set up some variables for the first pass
        phrase =  newPhrase()
        phrases = []
        nPhrase = True
        x = 0
        c = 0
        shift =  0.001
        lastEndTime = ""

        print("==> Creating phrases from transcript...")

        for item in items:

                # if it is a new phrase, then get the start_time of the first item
                if nPhrase == True:
                        if item["type"] == "pronunciation":
                                phrase["start_time"] = getTimeCode( float(item["start_time"]) + shift )
                                phrase["start_second"] = float(item["start_time"]) + shift
                                nPhrase = False
                                lastEndTime =  getTimeCode( float(item["end_time"]) + shift )
                        c+= 1
                else:   
                        # get the end_time if the item is a pronuciation and store it
                        # We need to determine if this pronunciation or puncuation here
                        # Punctuation doesn't contain timing information, so we'll want
                        # to set the end_time to whatever the last word in the phrase is.
                        if item["type"] == "pronunciation":
                                phrase["end_time"] = getTimeCode( float(item["end_time"]) + shift )
                                phrase["end_second"] =  float(item["end_time"]) + shift
                                
                # in either case, append the word to the phrase...
                # when the first word of the newline is a punctuation, append it to the previous line
                if c > 1 and x == 0 and item["type"] == "punctuation":
                        #print(c, item['alternatives'][0]["content"] )
                        phrases[-1]["words"].append(item['alternatives'][0]["content"])
                        phrases[-1]["punctuation"] = item['alternatives'][0]["content"]
                        #phrase["words"].append(item['alternatives'][0]["content"])
                else:
                        phrase["words"].append(item['alternatives'][0]["content"])
                        if item["type"] == "punctuation":
                            phrase["punctuation"] = item['alternatives'][0]["content"]
                        x += 1
                
                # now add the phrase to the phrases, generate a new phrase, etc.
                #if x == 10:
                if (x > 5 and item["type"] == "punctuation" ) or (x > 2 and item['alternatives'][0]["content"] == '.') or x == 12:
                        #print c, phrase
                        phrases.append(phrase)
                        phrase = newPhrase()
                        nPhrase = True
                        x = 0
        
        # if there are any words in the final phrase add to phrases  
        if(len(phrase["words"]) > 0):
                if phrase['end_time'] == '':
                        phrase['end_time'] = lastEndTime
                phrases.append(phrase)  
                                
        return phrases
        


# ==================================================================================
# Function: translateText
# Purpose: get the JSON response of translated text out of phrase
# Parameters: 
#                 txt - text
#                 sourceLangCode - the language code for the original content (e.g. English = "EN")
#                 targetLangCode - the language code for the translated content (e.g. Spanich = "ES")
#                 region - the AWS region in which to run the Translation (e.g. "us-east-1")
# ==================================================================================
def translateText( txt, sourceLangCode, targetLangCode, region ):
        # Get the translation in the target language.  We want to do this first so that the translation is in the full context
        # of what is said vs. 1 phrase at a time.  This really matters in some lanaguages

        # stringify the transcript
        #ts = json.loads( transcript )

        # pull out the transcript text and put it in the txt variable
        #txt = ts["results"]["transcripts"][0]["transcript"]
                
        #set up the Amazon Translate client
        translate = boto3.client(service_name='translate', region_name=region, use_ssl=True)
        
        # call Translate  with the text, source language code, and target language code.  The result is a JSON structure containing the 
        # translated text
        translation = translate.translate_text(Text=txt,SourceLanguageCode=sourceLangCode, TargetLanguageCode=targetLangCode)
        
        return translation

# ==================================================================================
# Function: translateTranscript
# Purpose: Based on the JSON transcript provided by Amazon Transcribe, get the JSON response of translated text
# Parameters: 
#                 transcript - the JSON output from Amazon Transcribe
#                 sourceLangCode - the language code for the original content (e.g. English = "EN")
#                 targetLangCode - the language code for the translated content (e.g. Spanich = "ES")
#                 region - the AWS region in which to run the Translation (e.g. "us-east-1")
# ==================================================================================
def translateTranscript( transcript, sourceLangCode, targetLangCode, region ):
        # Get the translation in the target language.  We want to do this first so that the translation is in the full context
        # of what is said vs. 1 phrase at a time.  This really matters in some lanaguages

        # stringify the transcript
        ts = json.loads( transcript )

        # pull out the transcript text and put it in the txt variable
        txt = ts["results"]["transcripts"][0]["transcript"]
                
        #set up the Amazon Translate client
        translate = boto3.client(service_name='translate', region_name=region, use_ssl=True)
        
        # call Translate  with the text, source language code, and target language code.  The result is a JSON structure containing the 
        # translated text
        translation = translate.translate_text(Text=txt,SourceLanguageCode=sourceLangCode, TargetLanguageCode=targetLangCode)
        
        return translation
        
        

# ==================================================================================
# Function: writeSRT
# Purpose: Iterate through the phrases and write them to the SRT file
# Parameters: 
#                 phrases - the array of JSON tuples containing the phrases to show up as subtitles
#                 filename - the name of the SRT output file (e.g. "mySRT.srt")
# ==================================================================================
def writeSRT( phrases, filename ):
        print ("==> Writing phrases to disk...")

        # open the files
        e = codecs.open(filename,"w+", "utf-8")
        x = 1
        
        for phrase in phrases:

                # determine how many words are in the phrase
                length = len(phrase["words"])
                
                # write out the phrase number
                e.write( str(x) + "\n" )
                x += 1
                
                # write out the start and end time
                e.write( phrase["start_time"] + " --> " + phrase["end_time"] + "\n" )
                                        
                # write out the full phase.  Use spacing if it is a word, or punctuation without spacing
                out = getPhraseText( phrase )

                # write out the srt file
                e.write(out + "\n\n" )
                

                #print out
                
        e.close()
        

# ==================================================================================
# Function: getPhraseText
# Purpose: For a given phrase, return the string of words including punctuation
# Parameters: 
#                 phrase - the array of JSON tuples containing the words to show up as subtitles
# ==================================================================================

def getPhraseText( phrase ):

        length = len(phrase["words"])
                
        out = ""
        for i in range( 0, length ):
                if not re.match( '[!"#$%&\'()*+,./:;<=>?@\^_`{|}~-]', phrase["words"][i]):
                #if re.match( '[a-zA-Z0-9]', phrase["words"][i]):
                        if i > 0:
                                out += " " + phrase["words"][i]
                        else:
                                out += phrase["words"][i]
                else:
                        out += phrase["words"][i]
                        
        return out
        

                        

        


        
        
