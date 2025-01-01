""" Convert SDRangel's FT8 log to eQSL.cc-compatible ADIF 3.1.3 format log """
from datetime import datetime, timezone
import re
import sys
import requests

class EQSLAGMembers:
    """ eQSL AG member class """
    __URL = "https://www.eqsl.cc/qslcard/DownloadedFiles/AGMemberList.txt"
    __members = []

    @classmethod
    def set(cls):
        """ Load eQSL.cc AG members list """
        print("Download eQSL.cc's Authenticity Guaranteed user list...")
        resp = requests.get(
            cls.__URL,
            timeout=100,
            headers={"Content-Type":"plain/text; charset=iso-8859-1"}
        )
        if resp.status_code == 200:
            print("Download was successfull!")
            cls.__members = resp.text.rstrip("\r\n").split("\r\n")[1:]
        else:
            sys.exit("Download failed, exiting...")

    @classmethod
    def get(cls):
        """ Return eQSL.cc AG members list """
        return cls.__members

class LogReader:
    """ SDRangel's FT8 log DB class """
    __records = []

    @classmethod
    def set(cls, filename):
        """ Read SDRangel's FT8 log to DB """
        print("Read input file " + filename + "...")
        try:
            with open(filename, "r", encoding="utf-8") as input_file:
                for line in input_file:
                    cols = line.strip("\n").split()
                    if len(cols) > 8:
                        qso_datetime = cols[0].split("_")
                        cls.__records.append({
                            "QSO_DATE": "20" + qso_datetime[0],
                            "TIME_ON": qso_datetime[1][0:4],
                            "CALL": cols[8],
                            "MODE": cols[3],
                            "FREQ": cols[1],
                            "RST_SENT": cols[4],
                            "QSLMSG": qso_datetime[1][0:6] + " UTC, " +
                            cols[6] + " Hz shift, " +
                            "msg:\"" + ' '.join(cols[7:]) + "\""
                        })
                print(
                    "... log size: " +
                    str(len(cls.__records)) +
                    " records."
                )
        except FileNotFoundError:
            sys.exit("Input file not found")

    @classmethod
    def get(cls):
        """ Return DB """
        return cls.__records

    @classmethod
    def remove_duplicated_calls(cls):
        """ Remove duplicated calls """
        out = []
        for old_element in cls.__records:
            if len(
                [new_element for new_element in out if new_element["CALL"] == old_element["CALL"]]
            ) == 0:
                out.append(old_element)
        print(
            "Remove duplicates: " +
            str(len(cls.__records)) + " --> " + str(len(out)) +
            " records."
        )
        cls.__records = out

    @classmethod
    def remove_long_callsign(cls):
        """ Remove duplicated calls """
        out = [element for element in cls.__records if len(element["CALL"]) <= 13]
        print(
            "Remove long callsigns: " +
            str(len(cls.__records)) + " --> " + str(len(out)) +
            " records."
        )
        cls.__records = out

    @classmethod
    def remove_cq_calls(cls):
        """ Remove duplicated calls """
        out = [element for element in cls.__records if not re.search(
            "msg:\"CQ ",
            element["QSLMSG"]
        )]
        print(
            "Remove CQ calls: " +
            str(len(cls.__records)) + " --> " + str(len(out)) +
            " records."
        )
        cls.__records = out

    @classmethod
    def remove_non_eqsl_ag_callsign(cls, eqsl_ag_db):
        """ Remove non eQSL AG-members' calls """
        out = [element for element in cls.__records if element["CALL"] in eqsl_ag_db]
        print(
            "Remove non-eQSL AG callsigns: " +
            str(len(cls.__records)) + " --> " + str(len(out)) +
            " records."
        )
        cls.__records = out

class LogWriter:
    """ eQSL.cc-compatible ADIF 3.1.3 format log class """
    __rows = []

    @classmethod
    def set(cls, lines, typ):
        """ Create ADIF-format rows """
        for line in lines:
            row = ''
            for field_name in line:
                row += "<" + field_name + ":"
                row += str(len(line[field_name])) + ">"
                row += line[field_name] + " "
            if typ == "header":
                row += "<EOH>\n"
            elif typ == "QSO":
                row += "<EOR>\n"
            cls.__rows.append(row)

    @classmethod
    def get(cls):
        """ Get ADIF-format rows """
        return cls.__rows

    @classmethod
    def write(cls, filename, rows):
        """ Write ADIF-format rows """
        print("Write output file " + filename + "...")
        try:
            with open(filename, "w", encoding="utf-8") as output_file:
                output_file.write(''.join(rows))
        except FileNotFoundError:
            sys.exit("Output file not found")

HEADER = [{
    "ADIF_VER": "3.1.3",
    "PROGRAMID": "SDRangelFT82ADIF",
    "PROGRAMVERSION": "1.0.0",
    "CREATED_TIMESTAMP": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
}]

if len(sys.argv) != 3:
    if sys.platform == "win32":
        print("Usage: python sdrangel_ft8_2_adif.py input.log output.adi")
    elif sys.platform == "linux":
        print("Usage: python3 sdrangel_ft8_2_adif.py input.log output.adi")
    print("input.log\t\tSDRangel's FT8 log file")
    print("output.adi\t\tADIF log file")
    sys.exit()

LogReader.set(sys.argv[1])
LogReader.remove_cq_calls()
LogReader.remove_duplicated_calls()
LogReader.remove_long_callsign()
EQSLAGMembers.set()
LogReader.remove_non_eqsl_ag_callsign(EQSLAGMembers.get())
LogWriter.set(HEADER, "header")
LogWriter.set(LogReader.get(), "QSO")
LogWriter.write(sys.argv[2], LogWriter.get())
