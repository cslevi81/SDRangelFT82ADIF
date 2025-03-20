""" Convert SDRangel's FT8 log to eQSL.cc-compatible ADIF 3.1.3 format log
"""
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
        print(
            "Download eQSL.cc's Authenticity Guaranteed user list... ",
            end=""
        )
        resp = requests.get(
            cls.__URL,
            timeout=100,
            headers={"Content-Type":"plain/text; charset=iso-8859-1"}
        )
        if resp.status_code == 200:
            cls.__members = resp.text.rstrip("\r\n").split("\r\n")[1:]
            print("...download was successfull (" + str(len(cls.__members)) + " records)!")
        else:
            sys.exit("...download failed, exiting...")

    @classmethod
    def get(cls):
        """ Return eQSL.cc AG members list """
        return set(cls.__members)

class LogReader:
    """ SDRangel's FT8 log DB class """
    __records = []

    @classmethod
    def set(cls, filename):
        """ Read SDRangel's FT8 log to DB """
        print(
            "Read input file " + filename + "... ",
            end=""
        )
        try:
            with open(filename, "r", encoding="utf-8") as input_file:
                for line in input_file:
                    cols = line.strip("\n").split()
                    if len(sys.argv) == 4 and sys.argv[3] == "ft8mon":
                        if len(cols) > 7 and re.match(r'^\d{6}', cols[0]):
                            cls.__records.append({
                                "QSO_DATE": filename[-12:-4],
                                "TIME_ON": cols[0],
                                "CALL": cols[6],
                                "CALLED": cols[5], # !!!
                                "MODE": "FT8",
                                "FREQ": "7.074",
                                "AUD_FREQ": cols[4], # !!!
                                "RST_SENT": cols[1],
                                "THIRD_ROW": cols[7] # !!!
                            })
                    else:
                        if len(cols) > 8:
                            qso_datetime = cols[0].split("_")
                            cls.__records.append({
                                "QSO_DATE": "20" + qso_datetime[0],
                                "TIME_ON": qso_datetime[1],
                                "CALL": cols[8],
                                "CALLED": cols[7], # !!!
                                "MODE": cols[3],
                                "FREQ": cols[1],
                                "AUD_FREQ": cols[6], # !!!
                                "RST_SENT": cols[4],
                                "THIRD_ROW": cols[9] if len(cols) > 9 else "" # !!!
                            })
                print(
                    "... log size: " +
                    str(len(cls.__records)) +
                    " records."
                )
        except FileNotFoundError:
            sys.exit("...input file not found")

    @classmethod
    def get(cls):
        """ Return DB """
        return cls.__records

class SeparateLog:
    """ Separate log to conservations """
    __conservations = {}

    @classmethod
    def add_to_cons(cls, step, rec):
        acon = {
            "LAST_TIME": rec["TIME_ON"],
            "AUD_FREQ": rec["AUD_FREQ"],
            "RST_SENT": rec["RST_SENT"],
            "THIRD_ROW": rec["THIRD_ROW"]
        }
        if step % 2 == 0:
            cls.__conservations[rec["CALLED"]][rec["CALL"]].append(acon)
        else:
            cls.__conservations[rec["CALL"]][rec["CALLED"]].append(acon)

    @classmethod
    def log(cls, step, rec):
        """ For debug """
        print(
            rec["TIME_ON"] + " " +
            str(step) + ". " +
            rec["CALLED"] + " " +
            rec["CALL"] + " " +
            rec["THIRD_ROW"]
        )

    @classmethod
    def process(cls, step, rec):
        """ Separate received messages by steps """
        regex = {
            "LOC": r"^[A-R]{2}[0-9]{2}$",
            "RST": r"^[\-\+]+[0-9]{2}$",
            "RRST": r"^R[\-\+]+[0-9]{2}$",
            "GOODBYE": r"^RRR|(RR)?73$"
        }
        match step:
            case 1:
                if rec["CALLED"] ==  "CQ":
                    if rec["CALL"] not in cls.__conservations:
                        cls.__conservations[
                            rec["CALL"]
                        ] = {
                            "LAST_TIME": rec["TIME_ON"],
                            "QSO_DATE": rec["QSO_DATE"],
                            "MODE": rec["MODE"],
                            "FREQ": rec["FREQ"],
                            "RST_SENT": rec["RST_SENT"]
                        }
                    else:
                        cls.__conservations[
                            rec["CALL"]
                        ][
                            "LAST_TIME"
                        ] = rec["TIME_ON"]
                    return True
            case 2:
                if (
                    rec["CALLED"] in cls.__conservations and
                    re.match(
                        regex["LOC"],
                        rec["THIRD_ROW"]
                    ) and int(
                        cls.__conservations[rec["CALLED"]]["LAST_TIME"]
                    ) < int(
                        rec["TIME_ON"]
                    )
                ):
                    cls.__conservations[rec["CALLED"]][rec["CALL"]] = []
                    cls.add_to_cons(step, rec)
                    return True
            case 3:
                if (
                    rec["CALL"] in cls.__conservations and
                    rec["CALLED"] in cls.__conservations[rec["CALL"]] and len(
                        cls.__conservations[rec["CALL"]][rec["CALLED"]]
                    ) == (step - 2) and re.match(
                        regex["RST"],
                        rec["THIRD_ROW"]
                    ) and re.match(
                        regex["LOC"],
                        cls.__conservations[rec["CALL"]][rec["CALLED"]][-1]["THIRD_ROW"]
                    ) and int(
                        cls.__conservations[rec["CALL"]][rec["CALLED"]][-1]["LAST_TIME"]
                    ) < int(
                        rec["TIME_ON"]
                    )
                ):
                    cls.add_to_cons(step, rec)
                    return True
            case 4:
                if (
                    rec["CALLED"] in cls.__conservations and
                    rec["CALL"] in cls.__conservations[rec["CALLED"]] and len(
                    cls.__conservations[rec["CALLED"]][rec["CALL"]]
                    ) == (step - 2) and re.match(
                        regex["RRST"],
                        rec["THIRD_ROW"]
                    ) and re.match(
                        regex["RST"],
                        cls.__conservations[rec["CALLED"]][rec["CALL"]][-1]["THIRD_ROW"]
                    ) and int(
                        cls.__conservations[rec["CALLED"]][rec["CALL"]][-1]["LAST_TIME"]
                    ) < int(
                        rec["TIME_ON"]
                    )
                ):
                    cls.add_to_cons(step, rec)
                    return True
            case 5:
                if (
                    rec["CALL"] in cls.__conservations and
                    rec["CALLED"] in cls.__conservations[rec["CALL"]] and
                    len(
                        cls.__conservations[rec["CALL"]][rec["CALLED"]]
                    ) == (step - 2) and re.match(
                        regex["GOODBYE"],
                        rec["THIRD_ROW"]
                    ) and re.match(
                        regex["RRST"],
                        cls.__conservations[rec["CALL"]][rec["CALLED"]][-1]["THIRD_ROW"]
                    ) and int(
                        cls.__conservations[rec["CALL"]][rec["CALLED"]][-1]["LAST_TIME"]
                    ) < int(
                        rec["TIME_ON"]
                    )
                ):
                    cls.add_to_cons(step, rec)
                    return True
            case 6:
                if (
                    rec["CALLED"] in cls.__conservations and
                    rec["CALL"] in cls.__conservations[rec["CALLED"]] and
                    len(
                        cls.__conservations[rec["CALLED"]][rec["CALL"]]
                    ) == (step - 2) and
                    re.match(
                        regex["GOODBYE"],
                        rec["THIRD_ROW"]
                    ) and
                    re.match(
                        regex["GOODBYE"],
                        cls.__conservations[rec["CALLED"]][rec["CALL"]][-1]["THIRD_ROW"]
                    ) and int(
                        cls.__conservations[rec["CALLED"]][rec["CALL"]][-1]["LAST_TIME"]
                    ) < int(
                        rec["TIME_ON"]
                    )
                ):
                    cls.add_to_cons(step, rec)
                    return True
            case 7:
                if (
                    rec["CALL"] in cls.__conservations and
                    rec["CALLED"] in cls.__conservations[rec["CALL"]] and
                    len(
                        cls.__conservations[rec["CALL"]][rec["CALLED"]]
                    ) == (step - 2) and
                    re.match(
                        regex["GOODBYE"],
                        rec["THIRD_ROW"]
                    ) and
                    re.match(
                        regex["GOODBYE"],
                        cls.__conservations[rec["CALL"]][rec["CALLED"]][-1]["THIRD_ROW"]
                    ) and int(
                        cls.__conservations[rec["CALL"]][rec["CALLED"]][-1]["LAST_TIME"]
                    ) < int(
                        rec["TIME_ON"]
                    )
                ):
                    cls.add_to_cons(step, rec)
                    return True
    @classmethod
    def remove_non_eqsl_ag_callsign(cls, log, eqsl_ag_db):
        """ Remove non eQSL AG-members' calls """
        out = [
            element for element in log if
                element["CALL"] in eqsl_ag_db and
                element["CALLED"] in eqsl_ag_db or
                element["CALLED"] == "CQ"
        ]
        print(
            "..." +
            str(len(log)) + " --> " + str(len(out)) +
            " records."
        )
        return out

    @classmethod
    def get(cls, log):
        """ Get conservations """
        print(
            "Remove non-eQSL AG callsigns... ",
            end=""
        )
        filtered_log = cls.remove_non_eqsl_ag_callsign(
            log,
            EQSLAGMembers.get()
        )
        print(
            "Separate log to callers... ",
            end=""
        )
        for record in filtered_log:
            for s in range(1, 8):
                if cls.process(s, record):
                    break

        print("..." + str(len(cls.__conservations)) + " callers.")
        out = []
        for call in cls.__conservations:
            for called in cls.__conservations[call]:
                if (
                    called != "LAST_TIME" and
                    called != "QSO_DATE" and
                    called != "MODE" and
                    called != "FREQ" and
                    called != "RST_SENT" and
                    len(cls.__conservations[call][called]) > 3
                ):
                    qsl_row = {}
                    qsl_row["CALL"] = call
                    qsl_row["QSO_DATE"] = cls.__conservations[call]["QSO_DATE"]
                    qsl_row["MODE"] = cls.__conservations[call]["MODE"]
                    qsl_row["FREQ"] = cls.__conservations[call]["FREQ"]
                    qsl_row["RST_SENT"] = cls.__conservations[call]["RST_SENT"]
                    qslmsg_col = []
                    for step in range(len(cls.__conservations[call][called])):
                        c = cls.__conservations[call][called][step]
                        qslmsg_row = c["LAST_TIME"] + " "
                        qslmsg_row += c["AUD_FREQ"] + "Hz \""
                        qslmsg_row += (called if step % 2 else call) + " "
                        qslmsg_row += (call if step % 2 else called) + " "
                        qslmsg_row += c["THIRD_ROW"] + "\""
                        qslmsg_col.append(qslmsg_row)
                        if step % 2:
                            qsl_row["TIME_ON"] = c["LAST_TIME"]
                    if len(qslmsg_col) == 4 or len(qslmsg_col) == 5 or len(qslmsg_col) == 6:
                        qsl_row["QSLMSG"] = ' | '.join(qslmsg_col)
                    out.append(qsl_row)
        return out


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
    def remove_duplicate(cls, lines):
        """ Remove duplicates """
        out = []
        print("Remove duplicates...", end="")
        for old_element in lines:
            found = False
            for new_element in out:
                if (
                    new_element["CALL"] == old_element["CALL"] and
                    new_element["TIME_ON"][0:4] == old_element["TIME_ON"][0:4]
                ):
                    found = True
                    break
            if not found:
                out.append(old_element)
        print(
            "..." +
            str(len(lines)) +
            " --> " +
            str(len(out)) +
            " records."
        )
        return out

    @classmethod
    def write(cls, filename, rows):
        """ Write ADIF-format rows """
        print("Write output file " + filename + "... ", end="")
        try:
            with open(filename, "w", encoding="utf-8") as output_file:
                output_file.write(''.join(rows))
                print("..." + str(len(rows)) + " rows written.")
        except FileNotFoundError:
            sys.exit("Output file not found")

HEADER = [{
    "ADIF_VER": "3.1.3",
    "PROGRAMID": "SDRangelFT82ADIF",
    "PROGRAMVERSION": "2.0.0",
    "CREATED_TIMESTAMP": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
}]

if len(sys.argv) != 3 and len(sys.argv) != 4:
    if sys.platform == "win32":
        print("Usage: python sdrangel_ft8_2_adif.py input.log output.adi [ft8mon]")
    elif sys.platform == "linux":
        print("Usage: python3 sdrangel_ft8_2_adif.py input.log output.adi [ft8mon]")
    print("input.log\t\tSDRangel's FT8 log file")
    print("output.adi\t\tADIF log file")
    print("ft8mon\t\t(optional) if input log is come from ft8mon")
    sys.exit()

EQSLAGMembers.set()
LogReader.set(sys.argv[1])

res = SeparateLog.get(
    LogReader.get()
)

LogWriter.set(HEADER, "header")
LogWriter.set(
    LogWriter.remove_duplicate(res),
    "QSO"
)
LogWriter.write(sys.argv[2], LogWriter.get())
