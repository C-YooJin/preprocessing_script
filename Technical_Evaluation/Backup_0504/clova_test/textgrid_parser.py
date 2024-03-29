#import calc3
#import fnmatch
import re
import os
import csv
import files_dirs

TEXTTIER = "TextTier"
INTERVALTIER = "IntervalTier"

OOTEXTFILE = re.compile(r"""(?x)
            xmin\ =\ (.*)[\r\n]+
            xmax\ =\ (.*)[\r\n]+
            [\s\S]+?size\ =\ (.*)[\r\n]+ 
""")

CHRONTEXTFILE = re.compile(r"""(?x)
            [\r\n]+(\S+)\ 
            (\S+)\ +!\ Time\ domain.\ *[\r\n]+
            (\S+)\ +!\ Number\ of\ tiers.\ *[\r\n]+"
""")

OLDOOTEXTFILE = re.compile(r"""(?x)
            [\r\n]+(\S+)
            [\r\n]+(\S+)
            [\r\n]+.+[\r\n]+(\S+)
""")


# TextGrid Class

class TextGrid(object):
    """
    Class to manipulate the TextGrid format used by Praat.
    Separates each tier within this file into its own Tier
    object.  Each TextGrid object has
    a number of tiers (size), xmin, xmax, a text type to help
    with the different styles of TextGrid format, and tiers with their
    own attributes.
    """

    def __init__(self, file_name, read_file):
        """
        Takes open read file as input, initializes attributes
        of the TextGrid file.
        @type read_file: An open TextGrid file, mode "r".
        @param size:  Number of tiers.
        @param xmin: xmin.
        @param xmax: xmax.
        @param t_time:  Total time of TextGrid file.
        @param text_type:  TextGrid format.
        @type tiers:  A list of tier objects.
        """

        self.read_file = read_file
        self.file_name = os.path.splitext(file_name)[0]
        self.size = 0
        self.xmin = 0
        self.xmax = 0
        self.t_time = 0
        self.text_type = self._check_type()
        self.tiers = self._find_tiers()

    def __iter__(self):
        for tier in self.tiers:
            yield tier

    def next(self):
        if self.idx == (self.size - 1):
            raise StopIteration
        self.idx += 1
        return self.tiers[self.idx]

    @staticmethod
    def load(file):
        """
        @param file: a file in TextGrid format
        """

        return TextGrid(open(file).read())

    def _load_tiers(self, header):
        """
        Iterates over each tier and grabs tier information.
        """

        tiers = []
        if self.text_type == "ChronTextFile":
            m = re.compile(header)
            tier_headers = m.findall(self.read_file)
            tier_re = " \d+.?\d* \d+.?\d*[\r\n]+\"[^\"]*\""
            for i in range(0, self.size):
                tier_info = [tier_headers[i]] + \
                            re.findall(str(i + 1) + tier_re, self.read_file)
                tier_info = "\n".join(tier_info)
                tiers.append(Tier(tier_info, self.text_type, self.t_time))
            return tiers

        tier_re = header + "[\s\S]+?(?=" + header + "|$$)"
        m = re.compile(tier_re)
        tier_iter = m.finditer(self.read_file)
        for iterator in tier_iter:
            (begin, end) = iterator.span()
            tier_info = self.read_file[begin:end]
            tiers.append(Tier(tier_info, self.text_type, self.t_time))
        return tiers

    def _check_type(self):
        """
        Figures out the TextGrid format.
        """

        m = re.match("(.*)[\r\n](.*)[\r\n](.*)[\r\n](.*)", self.read_file)
        try:
            type_id = m.group(1).strip()
        except AttributeError:
            raise TypeError("Cannot read file -- try TextGrid.load()")
        xmin = m.group(4)
        if type_id == "File type = \"ooTextFile\"":
            if "xmin" not in xmin:
                text_type = "OldooTextFile"
            else:
                text_type = "ooTextFile"
        elif type_id == "\"Praat chronological TextGrid text file\"":
            text_type = "ChronTextFile"
        else:
            raise TypeError("Unknown format '(%s)'", (type_id))
        return text_type

    def _find_tiers(self):
        """
        Splits the textgrid file into substrings corresponding to tiers.
        """

        if self.text_type == "ooTextFile":
            m = OOTEXTFILE
            header = " +item \["
        elif self.text_type == "ChronTextFile":
            m = CHRONTEXTFILE
            header = "\"\S+\" \".*\" \d+\.?\d* \d+\.?\d*"
        elif self.text_type == "OldooTextFile":
            m = OLDOOTEXTFILE
            header = "\".*\"[\r\n]+\".*\""

        file_info = m.findall(self.read_file)[0]
        self.xmin = float(file_info[0])
        self.xmax = float(file_info[1])
        self.t_time = self.xmax - self.xmin
        self.size = int(file_info[2])
        tiers = self._load_tiers(header)
        return tiers

    def to_chron(self):
        """
        @return:  String in Chronological TextGrid file format.
        """

        chron_file = ""
        chron_file += "\"Praat chronological TextGrid text file\"\n"
        chron_file += str(self.xmin) + " " + str(self.xmax)
        chron_file += "   ! Time domain.\n"
        chron_file += str(self.size) + "   ! Number of tiers.\n"
        for tier in self.tiers:
            idx = (self.tiers.index(tier)) + 1
            tier_header = "\"" + tier.classid + "\" \"" \
                          + tier.nameid + "\" " + str(tier.xmin) \
                          + " " + str(tier.xmax)
            chron_file += tier_header + "\n"
            transcript = tier.simple_transcript
            for (xmin, xmax, utt) in transcript:
                chron_file += str(idx) + " " + str(xmin)
                chron_file += " " + str(xmax) + "\n"
                chron_file += "\"" + utt + "\"\n"
        return chron_file

    def to_oo(self):
        """
        @return:  A string in OoTextGrid file format.
        """

        oo_file = ""
        oo_file += "File type = \"ooTextFile\"\n"
        oo_file += "Object class = \"TextGrid\"\n\n"
        oo_file += "xmin = ", self.xmin, "\n"
        oo_file += "xmax = ", self.xmax, "\n"
        oo_file += "tiers? <exists>\n"
        oo_file += "size = ", self.size, "\n"
        oo_file += "item []:\n"
        for i in range(len(self.tiers)):
            oo_file += "%4s%s [%s]" % ("", "item", i + 1)
            _curr_tier = self.tiers[i]
            for (x, y) in _curr_tier.header:
                oo_file += "%8s%s = \"%s\"" % ("", x, y)
            if _curr_tier.classid != TEXTTIER:
                for (xmin, xmax, text) in _curr_tier.simple_transcript:
                    oo_file += "%12s%s = %s" % ("", "xmin", xmin)
                    oo_file += "%12s%s = %s" % ("", "xmax", xmax)
                    oo_file += "%12s%s = \"%s\"" % ("", "text", text)
            else:
                for (time, mark) in _curr_tier.simple_transcript:
                    oo_file += "%12s%s = %s" % ("", "time", time)
                    oo_file += "%12s%s = %s" % ("", "mark", mark)
        return oo_file


# Tier Class

class Tier(object):
    """
    A container for each tier.
    """

    def __init__(self, tier, text_type, t_time):
        """
        Initializes attributes of the tier: class, name, xmin, xmax
        size, transcript, total time.
        Utilizes text_type to guide how to parse the file.
        @type tier: a tier object; single item in the TextGrid list.
        @param text_type:  TextGrid format
        @param t_time:  Total time of TextGrid file.
        @param classid:  Type of tier (point or interval).
        @param nameid:  Name of tier.
        @param xmin:  xmin of the tier.
        @param xmax:  xmax of the tier.
        @param size:  Number of entries in the tier
        @param transcript:  The raw transcript for the tier.
        """

        self.tier = tier
        self.text_type = text_type
        self.t_time = t_time
        self.classid = ""
        self.nameid = ""
        self.xmin = 0
        self.xmax = 0
        self.size = 0
        self.transcript = ""
        self.tier_info = ""
        self._make_info()
        self.simple_transcript = self.make_simple_transcript()
        if self.classid != TEXTTIER:
            self.mark_type = "intervals"
        else:
            self.mark_type = "points"
            self.header = [("class", self.classid), ("name", self.nameid), \
                           ("xmin", self.xmin), ("xmax", self.xmax), ("size", self.size)]

    def __iter__(self):
        return self

    def _make_info(self):
        """
        Figures out most attributes of the tier object:
        class, name, xmin, xmax, transcript.
        """

        trans = "([\S\s]*)"
        if self.text_type == "ChronTextFile":
            classid = "\"(.*)\" +"
            nameid = "\"(.*)\" +"
            xmin = "(\d+\.?\d*) +"
            xmax = "(\d+\.?\d*) *[\r\n]+"
            # No size values are given in the Chronological Text File format.
            self.size = None
            size = ""
        elif self.text_type == "ooTextFile":
            classid = " +class = \"(.*)\" *[\r\n]+"
            nameid = " +name = \"(.*)\" *[\r\n]+"
            xmin = " +xmin = (\d+\.?\d*) *[\r\n]+"
            xmax = " +xmax = (\d+\.?\d*) *[\r\n]+"
            size = " +\S+: size = (\d+) *[\r\n]+"
        elif self.text_type == "OldooTextFile":
            classid = "\"(.*)\" *[\r\n]+"
            nameid = "\"(.*)\" *[\r\n]+"
            xmin = "(\d+\.?\d*) *[\r\n]+"
            xmax = "(\d+\.?\d*) *[\r\n]+"
            size = "(\d+) *[\r\n]+"
        m = re.compile(classid + nameid + xmin + xmax + size + trans)
        self.tier_info = m.findall(self.tier)[0]
        self.classid = self.tier_info[0]
        self.nameid = self.tier_info[1]
        self.xmin = float(self.tier_info[2])
        self.xmax = float(self.tier_info[3])
        if self.size != None:
            self.size = int(self.tier_info[4])
        self.transcript = self.tier_info[-1]

    def make_simple_transcript(self):
        """
        @return:  Transcript of the tier, in form [(start_time end_time label)]
        """

        if self.text_type == "ChronTextFile":
            trans_head = ""
            trans_xmin = " (\S+)"
            trans_xmax = " (\S+)[\r\n]+"
            trans_text = "\"([\S\s]*?)\""
        elif self.text_type == "ooTextFile":
            trans_head = " +\S+ \[\d+\]: *[\r\n]+"
            trans_xmin = " +\S+ = (\S+) *[\r\n]+"
            trans_xmax = " +\S+ = (\S+) *[\r\n]+"
            trans_text = " +\S+ = \"([^\"]*?)\""
        elif self.text_type == "OldooTextFile":
            trans_head = ""
            trans_xmin = "(.*)[\r\n]+"
            trans_xmax = "(.*)[\r\n]+"
            trans_text = "\"([\S\s]*?)\""
        if self.classid == TEXTTIER:
            trans_xmin = ""
        trans_m = re.compile(trans_head + trans_xmin + trans_xmax + trans_text)
        self.simple_transcript = trans_m.findall(self.transcript)
        return self.simple_transcript

    def transcript(self):
        """
        @return:  Transcript of the tier, as it appears in the file.
        """

        return self.transcript

    def time(self, non_speech_char="."):
        """
        @return: Utterance time of a given tier.
        Screens out entries that begin with a non-speech marker.
        """

        total = 0.0
        if self.classid != TEXTTIER:
            for (time1, time2, utt) in self.simple_transcript:
                utt = utt.strip()
                if utt and not utt[0] == ".":
                    total += (float(time2) - float(time1))
        return total

    def tier_name(self):
        """
        @return:  Tier name of a given tier.
        """

        return self.nameid

    def classid(self):
        """
        @return:  Type of transcription on tier.
        """

        return self.classid

    def min_max(self):
        """
        @return:  (xmin, xmax) tuple for a given tier.
        """

        return (self.xmin, self.xmax)

    def __repr__(self):
        return "<%s \"%s\" (%.2f, %.2f) %.2f%%>" % (
        self.classid, self.nameid, self.xmin, self.xmax, 100 * self.time() / self.t_time)

    def __str__(self):
        return self.__repr__() + "\n  " + "\n  ".join(" ".join(row) for row in self.simple_transcript)


def tg2csv(subdirpath, find_these):
    """
    Parses each TextGrid file and creates / saves one CSV file for each TextGrid file.
    Each CSV file has summarized information of the TextGrid file.
    Each row of the CSV file corresponds to each interval of the TextGrid file.
    Use the praat script to create labels first and then run this function.
    :param lbpath: path of the directory that contains TextGrid(s)
    :param find_these: specifying file format as .TextGrid
    :return: None
    """

    grids = []
    # Get all the TextGrid files
    tgfilelist = files_dirs.get_files(subdirpath, format=find_these)
    print(tgfilelist)
    # Put all TextGrid objects in a list
    for filename in tgfilelist:
        f = open(filename, 'r', encoding='utf8')
        data = f.read()
        tgrid = TextGrid(filename, data)
        grids.append(tgrid)
        f.close()

    # Parse TextGrids
    for grid in grids:
        tier = grid.tiers[0]
        #result_file = subdirpath+'/'+os.path.splitext(grid.file_name)[0]+'.csv'
        result_file = os.path.splitext(grid.file_name)[0]+'.csv'
        #print(result_file)
        with open(result_file, 'w', encoding='utf8') as out:
            csv_out = csv.writer(out)
            csv_out.writerow(["xmin", "xmax", "label"])

            # Write each TextGrid interval to CSV file
            for row in tier.simple_transcript:
                csv_out.writerow(row)