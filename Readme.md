# SDRangelFT82ADIF

The **SDRangelFT82ADIF** is a Python3-script, that converts the [SDRangel's FT8 log](https://github.com/f4exb/sdrangel/blob/master/plugins/channelrx/demodft8/readme.md#c8-log-messages) to [eQSL.cc-compatible](https://www.eqsl.cc/qslcard/ADIFContentSpecs.cfm), [ADIF 3.1.3](https://www.adif.org/313/ADIF_313.htm)-format log.

## Prerequisites
- Python 3.x
- [requests](https://docs.python-requests.org/en/latest/index.html) module

## Usage
1. Clone the repository or download the sdrangel_ft8_2_adif.py file.
2. Open a terminal or command prompt and navigate to the directory, where the file is located.
3. Run the following command to start the program - in Linux:
    ```
    pip3 install -r requirements.txt
    python3 sdrangel_ft8_2_adif.py input.log output.adi
    ```
    in Windows:
    ```
    pip install -r requirements.txt
    python sdrangel_ft8_2_adif.py input.log output.adi
    ```
    the *input.log* is the path of the [SDRangel's FT8 log](https://github.com/f4exb/sdrangel/blob/master/plugins/channelrx/demodft8/readme.md#c8-log-messages), the *output.adi* is the path of the [eQSL.cc-compatible](https://www.eqsl.cc/qslcard/ADIFContentSpecs.cfm), [ADIF 3.1.3](https://www.adif.org/313/ADIF_313.htm)-format log