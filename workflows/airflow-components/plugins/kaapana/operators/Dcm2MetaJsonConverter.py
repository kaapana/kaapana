import os
import json
import logging
import pytz
from dateutil import parser
from datetime import datetime

class Dcm2MetaJsonConversionException(Exception):
    pass


class Dcm2MetaJsonConverter:
    
    def __init__(self,
                format_time : str = "%H:%M:%S.%f", 
                format_date : str = "%Y-%m-%d", 
                format_date_time : str = "%Y-%m-%d %H:%M:%S.%f",
                exception_on_error: bool = True,
                dict_path: str = None):
        self.format_time = format_time
        self.format_date = format_date
        self.format_date_time = format_date_time
        self.exit_on_error = exception_on_error
        self.log = logging.getLogger(__name__)

        if not dict_path:
            if 'DICT_PATH' in os.environ:
                self.dict_path = os.getenv('DICT_PATH')
            else:
                raise Exception("Dict Path not found")

        with open(self.dict_path, encoding='utf-8') as dict_data:
            self.dictionary = json.load(dict_data)


    def get_new_key(self, key):
        new_key = ""

        if key in self.dictionary:
            new_key = self.dictionary[key]
        else:
            self.log.warn("{}: Could not identify DICOM tag -> using plain tag instead...".format(key))
            new_key = key

        return new_key


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
                self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ could not convert time!")
                self.log.warn("time_str: {}".format(time_str))
                if self.exit_on_error:
                    raise Dcm2MetaJsonConversionException()

            # HH:mm:ss.SSSSS
            time_string = ("%02i:%02i:%02i.%06i" % (hour, minute, sec, fsec))
            # date_output = ("\"%02i:%02i:%02i.%03i\""%(hour,minute,sec,fsec))
            time_formatted = parser.parse(time_string).strftime(self.format_time)

            # time_formatted=convert_time_to_utc(time_formatted,format_time)

            return time_formatted

        except Exception as e:
            self.log.warn("##################################### COULD NOT EXTRACT TIME!!")
            self.log.warn("Value: {}".format(time_str))
            self.log.warn(e)
            if self.exit_on_error:
                raise Dcm2MetaJsonConversionException()


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
                        self.log.warn("Error list entry value type!")
                        self.log.warn("Needed-Type: {}".format(val_type))
                        self.log.warn("List: {}".format(str(obj)))
                        self.log.warn("Value: {}".format(element))
                        self.log.warn("Type: {}".format(type(element)))
                        return "SKIPIT"
            else:
                self.log.warn("Wrong data type!!")
                self.log.warn("Needed-Type: {}".format(val_type))
                self.log.warn("Value: {}".format(obj))
                return "SKIPIT"

        except Exception as e:
            self.log.warn("Error check value type!")
            self.log.warn("Needed-Type: {}".format(val_type))
            self.log.warn("Found-Type:  {}".format(type(obj)))
            self.log.warn("Value: {}".format(obj))
            self.log.warn(e)
            return "SKIPIT"

        return obj


    def convert_time_to_utc(self, time_berlin, date_format):
        local = pytz.timezone("Europe/Berlin")
        naive = datetime.strptime(time_berlin, date_format)
        local_dt = local.localize(naive, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)

        return utc_dt.strftime(date_format)


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
                    self.log.warn("Found NAN! -> skipping")
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
                            self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            self.log.warn("Could not extract age from: {}".format(value_str))
                            self.log.warn(e)
                            if self.exit_on_error:
                                raise Dcm2MetaJsonConversionException()

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
                            self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            self.log.warn("Could not extract date from: {}".format(value_str))
                            self.log.warn(e)
                            if self.exit_on_error:
                                raise Dcm2MetaJsonConversionException()

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
                            self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                raise Dcm2MetaJsonConversionException()

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
                                self.log.warn("DATE ONLY FOUND")
                                datestr_date = parser.parse(value_str).strftime("%Y%m%d")
                                datestr_time = parser.parse("01:00:00").strftime("%H:%M:%S")
                                date_time_string = datestr_date + " " + datestr_time

                            elif len(value_str) == 16:
                                self.log.info("DATETIME FOUND")
                                datestr_date = str(value_str)[:8]
                                datestr_time = str(value_str)[8:]
                                datestr_date = parser.parse(datestr_date).strftime(self.format_date)
                                datestr_time = parser.parse(datestr_time).strftime(self.format_time)
                                date_time_string = datestr_date + " " + datestr_time

                            else:
                                self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                                self.log.warn("++++++++++++++++++++++++++++ No Datetime ++++++++++++++++++++++++++++")
                                self.log.warn("KEY  : {}".format(new_key))
                                self.log.warn("Value: {}".format(value_str))
                                self.log.warn("LEN: {}".format(len(value_str)))
                                self.log.warn("Skipping...")
                                self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                                if self.exit_on_error:
                                    raise Dcm2MetaJsonConversionException()

                            if date_time_string is not None:

                                date_time_formatted = parser.parse(date_time_string).strftime(self.format_date_time)
                                date_time_formatted = self.convert_time_to_utc(date_time_formatted, self.format_date_time)

                                new_key = new_key+"_datetime"

                                self.log.warn("Value: {}".format(value_str))
                                self.log.warn("DATETIME: {}".format(date_time_formatted))
                                new_meta_data[new_key] = date_time_formatted

                        except Exception as e:
                            self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            self.log.warn("Could not extract Date Time from: {}".format(value_str))
                            self.log.warn(e)
                            if self.exit_on_error:
                                raise Dcm2MetaJsonConversionException()

                    elif vr == "FL":
                        # Floating Point Single
                        # Single precision binary floating point number represented in IEEE 754:1985 32-bit Floating Point Number Format.

                        new_key = new_key+"_float"

                        checked_val = self.check_type(value_str, float)
                        if checked_val != "SKIPIT":
                            new_meta_data[new_key] = checked_val
                        else:
                            self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                raise Dcm2MetaJsonConversionException()

                    elif vr == "FD":
                        # Floating Point Double
                        # Double precision binary floating point number represented in IEEE 754:1985 64-bit Floating Point Number Format.

                        new_key = new_key+"_float"

                        checked_val = self.check_type(value_str, float)
                        if checked_val != "SKIPIT":
                            new_meta_data[new_key] = checked_val
                        else:
                            self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                raise Dcm2MetaJsonConversionException()

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
                            self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                raise Dcm2MetaJsonConversionException()

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
                            self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                raise Dcm2MetaJsonConversionException()

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
                            self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                raise Dcm2MetaJsonConversionException()

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
                                        self.log.warn("Attention!")
                                        if self.exit_on_error:
                                            raise Dcm2MetaJsonConversionException()

                            else:
                                self.log.warn("ATTENTION!")
                                if self.exit_on_error:
                                    raise Dcm2MetaJsonConversionException()

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
                            self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                raise Dcm2MetaJsonConversionException()

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
                            self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                raise Dcm2MetaJsonConversionException()

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
                            self.log.warn("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ SKIPPED")
                            if self.exit_on_error:
                                raise Dcm2MetaJsonConversionException()

                    elif vr == "UT":
                        # Unlimited Text
                        # A character string that may contain one or more paragraphs. It may contain the Graphic Character set and the Control Characters, CR, LF,
                        # FF, and ESC. It may be padded with trailing spaces, which may be ignored, but leading spaces are considered to be significant.
                        # Data Elements with this VR shall not be multi-valued and therefore character code 5CH (the BACKSLASH "\" in ISO-IR 6) may be used.
                        new_key = new_key+"_keyword"
                        new_meta_data[new_key] = (value_str)

                    else:
                        self.log.warn(f"################ VR in ELSE!: {vr}")
                        self.log.warn(f"DICOM META: {dicom_meta[key]}")
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
                    raise Dcm2MetaJsonConversionException()

            else:
                if "InlineBinary" in value:
                    self.log.warn("##########################################################################        SKIPPING BINARY!")
                elif "Value" not in value:
                    self.log.warn("No value found in entry: {}".format(str(value).strip('[]').encode('utf-8')))
                elif "vr" not in value:
                    self.log.warn("No vr found in entry: {}".format(str(value).strip('[]').encode('utf-8')))
                else:
                    self.log.warn("##########################################################################        replace_tags ELSE!")
                    if "vr" in value:
                        self.log.warn("VR: {}".format(value["vr"].encode('utf-8')))
                    if "Value" in value:
                        entry_value = str(value["Value"]).strip('[]').encode('utf-8')
                        self.log.warn("value: {}".format(entry_value))

                    self.log.warn("new_key: {}".format(new_key))

        return new_meta_data


    def dcmJson2metaJson(self, dicom_metadata):
        """
        Removes unneccessary data from json objects like binary stuff
        """
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
            elif "00080023 ContentDate_date" in new_meta_data:
                time_tag_used = "ContentDate"
                extracted_date = new_meta_data["00080023 ContentDate_date"]
            elif "00080020 StudyDate_date" in new_meta_data:
                time_tag_used = "StudyDate"
                extracted_date = new_meta_data["00080020 StudyDate_date"]

            if "00080032 AcquisitionTime_time" in new_meta_data:
                time_tag_used +=" + AcquisitionTime"
                extracted_time = new_meta_data["00080032 AcquisitionTime_time"]
            elif "00080031 SeriesTime_time" in new_meta_data:
                time_tag_used +=" + SeriesTime"
                extracted_time = new_meta_data["00080031 SeriesTime_time"]
            elif "00080033 ContentTime_time" in new_meta_data:
                time_tag_used +=" + ContentTime"
                extracted_time = new_meta_data["00080033 ContentTime_time"]
            elif "00080030 StudyTime_time" in new_meta_data:
                time_tag_used +=" + StudyTime"
                extracted_time = new_meta_data["00080030 StudyTime_time"]
            
            if extracted_date == None:
                self.log.warn("###########################        NO AcquisitionDate! -> set to today")
                time_tag_used +="not found -> arriving date"
                extracted_date = datetime.now().strftime(self.format_date)

            if extracted_time == None:
                self.log.warn("###########################        NO AcquisitionTime! -> set to now")
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
                    self.log.warn(
                        "########################################################################################### DIFF IN AGE!")

            new_meta_data["00101010 PatientAge_integer"] = patient_age_scan

        return new_meta_data
