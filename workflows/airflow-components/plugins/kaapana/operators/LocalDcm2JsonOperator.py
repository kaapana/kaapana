# -*- coding: utf-8 -*-

import subprocess
import os
import fnmatch
import json
import yaml
from pathlib import Path
import shutil
import pathlib
from datetime import datetime
from dateutil import parser
import pytz
import traceback
import logging
import glob
from shutil import copyfile, rmtree
import errno
import re

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from kaapana.operators.HelperCaching import cache_operator_output


class LocalDcm2JsonOperator(KaapanaPythonBaseOperator):

    @cache_operator_output
    def start(self, ds, **kwargs):
        print("Starting moule dcm2json...")
        print(kwargs)

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        with open(self.dict_path, encoding='utf-8') as dict_data:
            self.dictionary = json.load(dict_data)

        for batch_element_dir in batch_folder:
            dcm_files = sorted(glob.glob(os.path.join(batch_element_dir, self.operator_in_dir, "*.dcm*"), recursive=True))

            if len(dcm_files) == 0:
                print("No dicom file found!")
                exit(1)

            print('length', len(dcm_files))
            for dcm_file_path in dcm_files:

                print(("Extracting metadata: %s" % dcm_file_path))

                target_dir = os.path.join(batch_element_dir, self.operator_out_dir)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                json_file_path = os.path.join(target_dir, "{}.json".format(os.path.basename(batch_element_dir)))

                if self.delete_private_tags:
                    print("Deleting private tags!")
                    command = "%s --no-backup --ignore-missing-tags --erase-all \"(0014,3080)\" --erase-all \"(7FE0,0008)\" --erase-all \"(7FE0,0009)\" --erase-all \"(7FE0,0010)\" %s;" % (
                        self.dcmodify_path, dcm_file_path)
                else:
                    command = "%s --no-backup --ignore-missing-tags --erase-all \"(0014,3080)\" --erase-all \"(7FE0,0008)\" --erase-all \"(7FE0,0009)\" --erase-all \"(7FE0,0010)\" %s;" % (
                        self.dcmodify_path, dcm_file_path)
                # (0014,3080) Bad Pixel Image
                # (7FE0,0008) Float Pixel Data
                # (7FE0,0009) Double Float Pixel Data
                # (7FE0,0010) Pixel Data
                ret = subprocess.call([command], shell=True)
                if ret != 0:
                    print("Something went wrong with dcmodify...")
                    exit(1)
                self.executeDcm2Json(dcm_file_path, json_file_path)

                json_dict = self.cleanJsonData(json_file_path)

                with open(json_file_path, "w", encoding='utf-8') as jsonData:
                    json.dump(json_dict, jsonData, indent=4, sort_keys=True, ensure_ascii=True)

                # shutil.rmtree(self.temp_dir)

                if self.bulk == False:
                    break

    def mkdir_p(self, path):
        try:
            os.makedirs(path)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    def executeDcm2Json(self, inputDcm, outputJson):
        """
        Executes a conversion service

        program -- path to the service
        arguments -- the arguments for the service
        """

        command = self.dcm2json_path + " " + \
            self.withAppostroph(inputDcm) + " " + \
            self.withAppostroph(outputJson)
        print(("Executing: " + command))
        ret = subprocess.call(command, shell=True)
        if ret != 0:
            print("Something went wrong with dcm2json...")
            exit(1)
        return

    def withAppostroph(self, content):
        return "\"" + content + "\""

    def get_new_key(self, key):
        new_key = ""

        if key in self.dictionary:
            new_key = self.dictionary[key]
        else:
            print("{}: Could not identify DICOM tag -> using plain tag instead...".format(key))
            new_key = key

        return new_key

    def check_type(self, obj, val_type):
        try:
            if isinstance(obj, val_type) or (val_type is float and isinstance(obj, int)):
                return obj
            elif val_type is float and not isinstance(obj, list):
                obj = float(obj)
                return obj
            elif val_type is int and not isinstance(obj, list):
                obj = int(obj)
                return obj
            elif isinstance(obj, list):
                for element in obj:
                    if val_type is float:
                        element = float(element)
                    elif val_type is int:
                        element = int(element)

                    elif not isinstance(element, val_type):
                        print("Error list entry value type!")
                        print("Needed-Type: {}".format(val_type))
                        print("List: {}".format(str(obj)))
                        print("Value: {}".format(element))
                        print("Type: {}".format(type(element)))
                        return "SKIPIT"
            else:
                print("Wrong data type!!")
                print("Needed-Type: {}".format(val_type))
                print("Value: {}".format(obj))
                return "SKIPIT"

        except Exception as e:
            print("Error check value type!")
            print("Needed-Type: {}".format(val_type))
            print("Found-Type:  {}".format(type(obj)))
            print("Value: {}".format(obj))
            print(e)
            return "SKIPIT"

        return obj

    def get_time(self, time_str):
        try:
            hour = 0
            minute = 0
            sec = 0
            fsec = 0
            if "." in time_str:
                time_str = time_str.split(".")
                if time_str[1] != "":
                    fsec = int(time_str[1])
                time_str = time_str[0]
            if len(time_str) == 6:
                hour = int(time_str[:2])
                minute = int(time_str[2:4])
                sec = int(time_str[4:6])
            elif len(time_str) == 4:
                minute = int(time_str[:2])
                sec = int(time_str[2:4])

            elif len(time_str) == 2:
                sec = int(time_str)

            else:
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ could not convert time!")
                print("time_str: {}".format(time_str))
                if self.exit_on_error:
                    exit(1)

            # HH:mm:ss.SSSSS
            time_string = ("%02i:%02i:%02i.%06i" % (hour, minute, sec, fsec))
            # date_output = ("\"%02i:%02i:%02i.%03i\""%(hour,minute,sec,fsec))
            time_formatted = parser.parse(time_string).strftime(self.format_time)

            # time_formatted=convert_time_to_utc(time_formatted,format_time)

            return time_formatted

        except Exception as e:
            print("##################################### COULD NOT EXTRACT TIME!!")
            print("Value: {}".format(time_str))
            print(e)
            if self.exit_on_error:
                exit(1)

    def check_list(self, value_list):
        tmp_data = []
        for element in value_list:
            if isinstance(element, dict):
                tags_replaced = self.replace_tags(element)
                tmp_data.append(tags_replaced)

            elif isinstance(element, list):
                tmp_data.append(self.check_list(element))

            else:
                tmp_data.append(element)

        return tmp_data

    def replace_tags(self, dicom_meta):
        new_meta_data = {}
        for key, value in list(dicom_meta.items()):
            new_key = ""
            new_key = self.get_new_key(key)
            if 'vr' in value and 'Value' in value:
                value_str = dicom_meta[key]['Value']
                vr = str(dicom_meta[key]['vr'])

                if "nan" in value_str:
                    print("Found NAN! -> skipping")
                    continue

                if isinstance(value_str, list):
                    if len(value_str) == 1:
                        value_str = value_str[0]

                try:  # vr list: http://dicom.nema.org/dicom/2013/output/chtml/part05/sect_6.2.html

                    if vr == "AE":
                        # Application Entity
                        # A string of characters that identifies an Application Entity with leading and trailing spaces (20H) being non-significant.
                        # A value consisting solely of spaces shall not be used.
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = value_str

                    elif vr == "AS":
                        # Age String
                        # A string of characters with one of the following formats -- nnnD, nnnW, nnnM, nnnY;
                        # where nnn shall contain the number of days for D, weeks for W, months for M, or years for Y.

                        # Example: "018M" would represent an age of 18 months.
                        try:
                            age_count = int(value_str[:3])
                            identifier = value_str[3:]

                            new_key = new_key+"_keyword"
                            new_meta_data[new_key] = value_str
                        except Exception as e:
                            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            print("Could not extract age from: {}".format(value_str))
                            print(e)
                            if self.exit_on_error:
                                exit(1)

                    elif vr == "AT":
                        # Attribute Tag
                        # Ordered pair of 16-bit unsigned integers that is the value of a Data Element Tag.
                        # Example: A Data Element Tag of (0018,00FF) would be encoded as a series of 4 bytes in a Little-Endian Transfer Syntax as 18H,00H,FFH,00H
                        #  and in a Big-Endian Transfer Syntax as 00H,18H,00H,FFH.

                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = value_str

                    elif vr == "CS":
                        # Code String
                        # A string of characters with leading or trailing spaces (20H) being non-significant.
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = value_str

                    elif vr == "DA":
                        # date
                        # A string of characters of the format YYYYMMDD; where YYYY shall contain year,
                        # MM shall contain the month, and DD shall contain the day, interpreted as a date of the Gregorian calendar system.
                        # Example:
                        # "19930822" would represent August 22, 1993.
                        # Note:
                        # The ACR-NEMA Standard 300 (predecessor to DICOM) supported a string of characters of the format
                        # YYYY.MM.DD for this VR. Use of this format is not compliant.
                        # See also DT VR in this table.
                        try:
                            if isinstance(value_str, list):
                                date_formatted = []
                                for date_str in value_str:
                                    if date_str == "":
                                        continue
                                    date_formatted.append(parser.parse(date_str).strftime(self.format_date))
                            else:
                                date_formatted = parser.parse(value_str).strftime(self.format_date)

                            new_key = new_key+"_date"
                            new_meta_data[new_key] = date_formatted
                        except Exception as e:
                            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            print("Could not extract date from: {}".format(value_str))
                            print(e)
                            if self.exit_on_error:
                                exit(1)

                    elif vr == "DS":
                        # Decimal String
                        # A string of characters representing either a fixed point number or a floating point number.
                        # A fixed point number shall contain only the characters 0-9 with an optional leading "+" or "-" and an optional "." to mark the decimal point.
                        # A floating point number shall be conveyed as defined in ANSI X3.9, with an "E" or "e" to indicate the start of the exponent.
                        # Decimal Strings may be padded with leading or trailing spaces. Embedded spaces are not allowed.

                        #  Note
                        #  Data Elements with multiple values using this VR may not be properly encoded if Explicit-VR transfer syntax is used
                        #  and the VL of this attribute exceeds 65534 bytes.

                        new_key = new_key+"_float"

                        checked_val = self.check_type(value_str, float)
                        if checked_val != "SKIPIT":
                            new_meta_data[new_key] = checked_val
                        else:
                            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                exit(1)

                    elif vr == "DT":
                        # Date Time
                        # A concatenated date-time character string in the format:
                        # YYYYMMDDHHMMSS.FFFFFF&ZZXX
                        # 20020904000000.000000
                        # "%Y-%m-%d %H:%M:%S.%f"
                        try:
                            date_time_string = None

                            if len(value_str) == 21 and "." in value_str:
                                date_time_string = parser.parse(value_str.split(".")[0]).strftime("%Y-%m-%d %H:%M:%S.%f")

                            elif len(value_str) == 8:
                                print("DATE ONLY FOUND")
                                datestr_date = parser.parse(value_str).strftime("%Y%m%d")
                                datestr_time = parser.parse("01:00:00").strftime("%H:%M:%S")
                                date_time_string = datestr_date + " " + datestr_time

                            elif len(value_str) == 16:
                                print("DATETIME FOUND")
                                datestr_date = str(value_str)[:8]
                                datestr_time = str(value_str)[8:]
                                datestr_date = parser.parse(datestr_date).strftime(self.format_date)
                                datestr_time = parser.parse(datestr_time).strftime(self.format_time)
                                date_time_string = datestr_date + " " + datestr_time

                            else:
                                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                                print("++++++++++++++++++++++++++++ No Datetime ++++++++++++++++++++++++++++")
                                print("KEY  : {}".format(new_key))
                                print("Value: {}".format(value_str))
                                print("LEN: {}".format(len(value_str)))
                                print("Skipping...")
                                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                                if self.exit_on_error:
                                    exit(1)

                            if date_time_string is not None:

                                date_time_formatted = parser.parse(date_time_string).strftime(self.format_date_time)
                                date_time_formatted = self.convert_time_to_utc(date_time_formatted, self.format_date_time)

                                new_key = new_key+"_datetime"

                                print("Value: {}".format(value_str))
                                print("DATETIME: {}".format(date_time_formatted))
                                new_meta_data[new_key] = date_time_formatted

                        except Exception as e:
                            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            print("Could not extract Date Time from: {}".format(value_str))
                            print(e)
                            if self.exit_on_error:
                                exit(1)

                    elif vr == "FL":
                        # Floating Point Single
                        # Single precision binary floating point number represented in IEEE 754:1985 32-bit Floating Point Number Format.

                        new_key = new_key+"_float"

                        checked_val = self.check_type(value_str, float)
                        if checked_val != "SKIPIT":
                            new_meta_data[new_key] = checked_val
                        else:
                            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                exit(1)

                    elif vr == "FD":
                        # Floating Point Double
                        # Double precision binary floating point number represented in IEEE 754:1985 64-bit Floating Point Number Format.

                        new_key = new_key+"_float"

                        checked_val = self.check_type(value_str, float)
                        if checked_val != "SKIPIT":
                            new_meta_data[new_key] = checked_val
                        else:
                            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                exit(1)

                    elif vr == "IS":
                        # Integer String
                        # A string of characters representing an Integer in base-10 (decimal), shall contain only the characters 0 - 9, with an optional leading "+" or "-". It may be padded with leading and/or trailing spaces. Embedded spaces are not allowed.
                        # The integer, n, represented shall be in the range:
                        # -231<= n <= (231-1).
                        new_key = new_key+"_integer"

                        checked_val = self.check_type(value_str, int)
                        if checked_val != "SKIPIT":
                            new_meta_data[new_key] = checked_val
                        else:
                            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                exit(1)

                    elif vr == "LO":
                        # Long String
                        # A character string that may be padded with leading and/or trailing spaces.
                        # The character code 5CH (the BACKSLASH "\" in ISO-IR 6) shall not be present, as it is used as the delimiter
                        # between values in multiple valued data elements. The string shall not have Control Characters except for ESC.
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = str(value_str)

                    elif vr == "LT":
                        # Long Text
                        # A character string that may contain one or more paragraphs.
                        #  It may contain the Graphic Character set and the Control Characters, CR, LF, FF, and ESC.
                        #  It may be padded with trailing spaces, which may be ignored, but leading spaces are considered to be significant.
                        #  Data Elements with this VR shall not be multi-valued and therefore character code 5CH
                        #  (the BACKSLASH "\" in ISO-IR 6) may be used.
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = value_str

                    elif vr == "OB":
                        # Other Byte String
                        # A string of bytes where the encoding of the contents is specified by the negotiated Transfer Syntax.
                        #  OB is a VR that is insensitive to Little/Big Endian byte ordering (see Section 7.3).
                        #  The string of bytes shall be padded with a single trailing NULL byte value (00H) when necessary to achieve even length.
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = value_str

                    elif vr == "OD":
                        # Other Double String
                        # A string of 64-bit IEEE 754:1985 floating point words.
                        # OD is a VR that requires byte swapping within each 64-bit word when changing between Little Endian and Big Endian byte ordering

                        new_key = new_key+"_float"

                        checked_val = self.check_type(value_str, float)
                        if checked_val != "SKIPIT":
                            new_meta_data[new_key] = checked_val
                        else:
                            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                exit(1)

                    elif vr == "OF":
                        # Other Float String
                        # A string of 32-bit IEEE 754:1985 floating point words.
                        # OF is a VR that requires byte swapping within each 32-bit word when changing between Little Endian and Big Endian byte ordering

                        new_key = new_key+"_float"

                        new_meta_data[new_key] = value_str

                    elif vr == "OW":
                        # Other Word String
                        # A string of 16-bit words where the encoding of the contents is specified by the negotiated Transfer Syntax.
                        #  OW is a VR that requires byte swapping within each word when changing between Little Endian and Big Endian byte ordering
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = value_str

                    elif vr == "PN":
                        # Person Name
                        # A character string encoded using a 5 component convention. The character code 5CH (the BACKSLASH "\"
                        # in ISO-IR 6) shall not be present, as it is used as the delimiter between values in multiple valued data
                        # elements. The string may be padded with trailing spaces. For human use, the five components in their order
                        # of occurrence are: family name complex, given name complex, middle name, name prefix, name suffix.
                        new_key = new_key+"_keyword"
                        subcategories = ['Alphabetic',
                                         'Ideographic', 'Phonetic']
                        for cat in subcategories:
                            if cat in value_str:
                                new_meta_data[new_key+"_" +
                                              cat.lower()] = value_str[cat]

                    elif vr == "SH":
                        # Short String
                        # A character string that may be padded with leading and/or trailing spaces. The character code 05CH
                        # (the BACKSLASH "\" in ISO-IR 6) shall not be present, as it is used as the delimiter between values
                        # for multiple data elements. The string shall not have Control Characters except ESC.
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = str(value_str)

                    elif vr == "UC":
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = str(value_str)

                    elif vr == "SL":
                        # Signed Long
                        # Signed binary integer 32 bits long in 2's complement form.
                        # Represents an integer, n, in the range:
                        # - 231<= n <= 231-1.
                        new_key = new_key+"_integer"

                        checked_val = self.check_type(value_str, int)
                        if checked_val != "SKIPIT":
                            new_meta_data[new_key] = checked_val
                        else:
                            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                exit(1)

                    elif vr == "SQ":
                        result = []
                        new_key = new_key+"_object"
                        if isinstance(value_str, list):
                            result = self.check_list(value_str)
                            if isinstance(result, dict):
                                new_meta_data[new_key] = result
                            elif isinstance(result, list):
                                for cat_id in range(len(result)):
                                    cat = result[cat_id]
                                    if isinstance(cat, dict):
                                        pass
                                        # todo blowing up index ...
                                        # new_meta_data[new_key+"_"+str(cat_id)] = cat
                                    else:
                                        print("Attention!")
                                        if self.exit_on_error:
                                            exit(1)

                            else:
                                print("ATTENTION!")
                                if self.exit_on_error:
                                    exit(1)

                        elif isinstance(value_str, dict):
                            new_key = new_key+"_object"
                            result = self.replace_tags(value_str)
                            new_meta_data[new_key] = result

                    elif vr == "SS":
                        # Signed Short
                        # Signed binary integer 16 bits long in 2's complement form. Represents an integer n in the range:
                        # -215<= n <= 215-1.
                        new_key = new_key+"_integer"

                        checked_val = self.check_type(value_str, int)
                        if checked_val != "SKIPIT":
                            new_meta_data[new_key] = checked_val
                        else:
                            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                exit(1)

                    elif vr == "ST":
                        # Short Text
                        # A character string that may contain one or more paragraphs.
                        # It may contain the Graphic Character set and the Control Characters, CR, LF, FF, and ESC.
                        #  It may be padded with trailing spaces, which may be ignored, but leading spaces are considered to be significant.
                        #  Data Elements with this VR shall not be multi-valued and therefore character code 5CH (the BACKSLASH "\" in ISO-IR 6) may be used.
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = value_str

                    elif vr == "TM":
                        # Time
                        # A string of characters of the format HHMMSS.FFFFFF; where HH contains hours (range "00" - "23"), MM contains minutes (range "00" - "59"),
                        # SS contains seconds (range "00" - "60"), and FFFFFF contains a fractional part of a second as small as 1 millionth of a second (range "000000" - "999999").
                        # A 24-hour clock is used. Midnight shall be represented by only "0000" since "2400" would violate the hour range. The string may be padded with trailing spaces.
                        # Leading and embedded spaces are not allowed. One or more of the components MM, SS, or FFFFFF may be unspecified as long as every component
                        # to the right of an unspecified component is also unspecified, which indicates that the value is not precise to the precision of those unspecified components.
                        # The FFFFFF component, if present, shall contain 1 to 6 digits. If FFFFFF is unspecified the preceding "." shall not be included.

                        # Examples:
                        # "070907.0705 " represents a time of 7 hours, 9 minutes and 7.0705 seconds.
                        # "1010" represents a time of 10 hours, and 10 minutes.
                        # "021 " is an invalid value.
                        # Note
                        # The ACR-NEMA Standard 300 (predecessor to DICOM) supported a string of characters of the format HH:MM:SS.frac for this VR. Use of this format is not compliant.
                        # See also DT VR in this table.
                        # The SS component may have a value of 60 only for a leap second.

                        if isinstance(value_str, list):
                            time_formatted = []
                            for time_str in value_str:
                                if time_str == "" or time_str is None:
                                    continue
                                time_formatted.append(self.get_time(time_str))
                        else:
                            time_formatted = self.get_time(value_str)

                        new_key = new_key+"_time"
                        new_meta_data[new_key] = time_formatted

                    elif vr == "UI":
                        # Unique Identifier (UID)
                        # A character string containing a UID that is used to uniquely identify a wide variety of items.
                        # The UID is a series of numeric components separated by the period "." character.
                        # If a Value Field containing one or more UIDs is an odd number of bytes in length,
                        # the Value Field shall be padded with a single trailing NULL (00H) character to ensure
                        # that the Value Field is an even number of bytes in length. See Section 9 and Annex B for a complete specification and examples.
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = str(value_str)

                    elif vr == "UL":
                        # Unsigned Long
                        # Unsigned binary integer 32 bits long. Represents an integer n in the range:
                        # 0 <= n < 232.

                        new_key = new_key+"_integer"

                        checked_val = self.check_type(value_str, int)
                        if checked_val != "SKIPIT":
                            new_meta_data[new_key] = checked_val
                        else:
                            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                exit(1)

                    elif vr == "UN":
                        # Unknown
                        # A string of bytes where the encoding of the contents is unknown.
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = value_str

                    elif vr == "US":
                        # Unsigned Short
                        # Unsigned binary integer 16 bits long. Represents integer n in the range:
                        # 0 <= n < 216.
                        new_key = new_key+"_integer"

                        checked_val = self.check_type(value_str, int)
                        if checked_val != "SKIPIT":
                            new_meta_data[new_key] = checked_val
                        else:
                            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                exit(1)

                    elif vr == "UT":
                        # Unlimited Text
                        # A character string that may contain one or more paragraphs. It may contain the Graphic Character set and the Control Characters, CR, LF,
                        # FF, and ESC. It may be padded with trailing spaces, which may be ignored, but leading spaces are considered to be significant.
                        # Data Elements with this VR shall not be multi-valued and therefore character code 5CH (the BACKSLASH "\" in ISO-IR 6) may be used.
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = (value_str)

                    else:
                        print(f"################ VR in ELSE!: {vr}")
                        print(f"DICOM META: {dicom_meta[key]}")
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = (value_str)

                except Exception as e:
                    logging.error("#")
                    logging.error("#")
                    logging.error("#")
                    logging.error("################################### EXCEPTION #######################################")
                    logging.error("#")
                    logging.error(f"DICOM META: {dicom_meta[key]}")
                    logging.error(traceback.format_exc())
                    logging.error(value_str)
                    logging.error(e)
                    logging.error("#")
                    logging.error("#")
                    logging.error("#")
                    exit(1)

            else:
                if "InlineBinary" in value:
                    print("##########################################################################        SKIPPING BINARY!")
                elif "Value" not in value:
                    print("No value found in entry: {}".format(str(value).strip('[]').encode('utf-8')))
                elif "vr" not in value:
                    print("No vr found in entry: {}".format(str(value).strip('[]').encode('utf-8')))
                else:
                    print("##########################################################################        replace_tags ELSE!")
                    if "vr" in value:
                        print("VR: {}".format(value["vr"].encode('utf-8')))
                    if "Value" in value:
                        entry_value = str(value["Value"]).strip('[]').encode('utf-8')
                        print("value: {}".format(entry_value))

                    print("new_key: {}".format(new_key))

        return new_meta_data

    def correct_json(self, file_path):
        print("ERROR IN JSON FILE -> Try to correct")
        try:
            with open(file_path, "r", encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(yaml_data, f, indent=4, sort_keys=True, ensure_ascii=False)
        except Exception as e:
            print("##########################################################################        correction of json file  failed!")
            print(e)
            exit(1)

    def cleanJsonData(self, path):
        """
        Removes unneccessary data from json objects like binary stuff
        """
        new_meta_data = {}

        path_tmp = path.replace(".json", "_tmp.json")
        os.rename(path, path_tmp)
        with open(path_tmp, "rt", encoding="utf-8") as fin:
            with open(path, "wt", encoding="utf-8") as fout:
                for line in fin:
                    line = line.replace(" .", " 0.")
                    m = re.search(r"[\+][\d]", line)
                    if m is not None:
                        group = m.group()
                        fout.write(line.replace('+', ''))
                    else:
                        fout.write(line)
        os.remove(path_tmp)
        try:
            with open(path, encoding='utf-8') as dicom_meta:
                dicom_metadata = json.load(dicom_meta)

        except Exception as e:
            print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ ERROR WHILE LOADING JSON!!")
            print(e)
            print("Try to correct...")
            self.correct_json(path)
            print("Try again...")
            with open(path, encoding='utf-8') as dicom_meta:
                dicom_metadata = json.load(dicom_meta)

        new_meta_data = self.replace_tags(dicom_metadata)

        if "0008002A AcquisitionDateTime_datetime" in new_meta_data:
            time_tag_used = "AcquisitionDateTime_datetime"
            date_time_formatted = new_meta_data["0008002A AcquisitionDateTime_datetime"]
        else:
            time_tag_used = ""
            extracted_date = None
            extracted_time = None
            if "00080022 AcquisitionDate_date" in new_meta_data:
                time_tag_used = "AcquisitionDate"
                extracted_date = new_meta_data["00080022 AcquisitionDate_date"]
            elif "00080021 SeriesDate_date" in new_meta_data:
                time_tag_used = "SeriesDate"
                extracted_date = new_meta_data["00080021 SeriesDate_date"]
            elif "00080020 StudyDate_date" in new_meta_data:
                time_tag_used = "StudyDate"
                extracted_date = new_meta_data["00080020 StudyDate_date"]
            elif "00080023 ContentDate_date" in new_meta_data:
                time_tag_used = "ContentDate"
                extracted_date = new_meta_data["00080023 ContentDate_date"]

            if "00080032 AcquisitionTime_time" in new_meta_data:
                time_tag_used +=" + AcquisitionTime"
                extracted_time = new_meta_data["00080032 AcquisitionTime_time"]
            elif "00080031 SeriesTime_time" in new_meta_data:
                time_tag_used +=" + SeriesTime"
                extracted_time = new_meta_data["00080031 SeriesTime_time"]
            elif "00080030 StudyTime_time" in new_meta_data:
                time_tag_used +=" + StudyTime"
                extracted_time = new_meta_data["00080030 StudyTime_time"]
            elif "00080033 ContentTime_time" in new_meta_data:
                time_tag_used +=" + ContentTime"
                extracted_time = new_meta_data["00080033 ContentTime_time"]
            
            if extracted_date == None:
                print("###########################        NO AcquisitionDate! -> set to today")
                time_tag_used +="not found -> arriving date"
                extracted_date = datetime.now().strftime(self.format_date)

            if extracted_time == None:
                print("###########################        NO AcquisitionTime! -> set to now")
                time_tag_used +=" + not found -> arriving time"
                extracted_time = datetime.now().strftime(self.format_time)

            date_time_string = extracted_date+" "+extracted_time
            date_time_formatted = parser.parse(date_time_string).strftime(self.format_date_time)

        
        date_time_formatted = self.convert_time_to_utc(date_time_formatted, self.format_date_time)
        new_meta_data["timestamp"] = date_time_formatted

        new_meta_data["timestamp_arrived_datetime"] = self.convert_time_to_utc(datetime.now().strftime(self.format_date_time), self.format_date_time)
        new_meta_data["dayofweek_integer"] = datetime.strptime(
            date_time_formatted, self.format_date_time).weekday()
        new_meta_data["time_tag_used_keyword"] = time_tag_used

        if "00100030 PatientBirthDate_date" in new_meta_data:
            birthdate = new_meta_data["00100030 PatientBirthDate_date"]

            birthday_datetime = datetime.strptime(birthdate, "%Y-%m-%d")

            series_datetime = datetime.strptime(
                date_time_formatted, self.format_date_time)
            patient_age_scan = series_datetime.year - birthday_datetime.year - \
                ((series_datetime.month, series_datetime.day) <
                 (birthday_datetime.month, birthday_datetime.day))

            if "00101010 PatientAge_keyword" in new_meta_data:
                age_meta = int(
                    new_meta_data["00101010 PatientAge_keyword"][:-1])
                if patient_age_scan is not age_meta:
                    print(
                        "########################################################################################### DIFF IN AGE!")

            new_meta_data["00101010 PatientAge_integer"] = patient_age_scan

        return new_meta_data

    def convert_time_to_utc(self, time_berlin, date_format):
        local = pytz.timezone("Europe/Berlin")
        naive = datetime.strptime(time_berlin, date_format)
        local_dt = local.localize(naive, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)

        return utc_dt.strftime(date_format)

    def __init__(self,
                 dag,
                 exit_on_error=False,
                 delete_private_tags=True,
                 bulk=False,
                 *args, **kwargs):

        self.dcmodify_path = 'dcmodify'
        self.dcm2json_path = 'dcm2json'
        self.format_time = "%H:%M:%S.%f"
        self.format_date = "%Y-%m-%d"
        self.format_date_time = "%Y-%m-%d %H:%M:%S.%f"
        self.bulk = bulk
        self.exit_on_error = exit_on_error
        self.delete_private_tags = delete_private_tags

        os.environ["PYTHONIOENCODING"] = "utf-8"
        if 'DCMDICTPATH' in os.environ and 'DICT_PATH' in os.environ:
            self.dcmdictpath = os.getenv('DCMDICTPATH')
            self.dict_path = os.getenv('DICT_PATH')
        else:
            print("++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("DCMDICTPATH or DICT_PATH ENV NOT FOUND!")
            print("dcmdictpath: {}".format(os.getenv('DCMDICTPATH')))
            print("dict_path: {}".format(os.getenv('DICT_PATH')))
            print("++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            exit(1)

        super().__init__(
            dag,
            name="dcm2json",
            python_callable=self.start,
            ram_mem_mb=10,
            *args, **kwargs
        )
