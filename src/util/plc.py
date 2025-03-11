from pylogix import PLC
from tabulate import tabulate
from time import sleep

class PLCData:
    def __init__(self, ip, tags):
        self.ip = ip
        self.tags = tags  # List of tag dictionaries
        self.plc = PLC()
        self.plc.IPAddress = ip
        self.tag_values = {}
        print(self.plc.Read("FROM_MACHINE_4C_PLC[0]"))

    def update(self):
        for tag in self.tags:
            tag_name = tag["tag_name"]  # Extract tag name
            response = self.plc.Read(tag_name)  # Read value from PLC
            [tag, temp, status] = str(response).split(' ')
            self.tag_values[tag_name] = temp  # Store the value
            
    def get_tags(self):
        return self.tag_values  # Return the latest tag values
    


if __name__ == "__main__":
    ip = "192.168.11.1"
    tags = [
        {"heater": "13", "key": "13", "tag_name": "FROM_MACHINE_4C_PLC[43]"},
        {"heater": "12", "key": "12", "tag_name": "FROM_MACHINE_4C_PLC[42]"},
        {"heater": "11", "key": "11", "tag_name": "FROM_MACHINE_4C_PLC[41]"},
        {"heater": "10", "key": "10", "tag_name": "FROM_MACHINE_4C_PLC[39]"},
        {"heater": "9",  "key": "9", "tag_name": "FROM_MACHINE_4C_PLC[38]"},
        {"heater": "8",  "key": "8", "tag_name": "FROM_MACHINE_4C_PLC[37]"},
        {"heater": "7",  "key": "7", "tag_name": "FROM_MACHINE_4C_PLC[36]"},
        {"heater": "", "key": "26", "tag_name": "FROM_MACHINE_4C_PLC[56]"},
        {"heater": "", "key": "25", "tag_name": "FROM_MACHINE_4C_PLC[55]"},
        {"heater": "", "key": "24", "tag_name": "FROM_MACHINE_4C_PLC[54]"},
        {"heater": "", "key": "23", "tag_name": "FROM_MACHINE_4C_PLC[53]"},
        {"heater": "", "key": "22", "tag_name": "FROM_MACHINE_4C_PLC[52]"},
        {"heater": "", "key": "21", "tag_name": "FROM_MACHINE_4C_PLC[51]"},
        {"heater": "", "key": "20", "tag_name": "FROM_MACHINE_4C_PLC[50]"},
    ]



    # Create PLCData instance
    plc_data = PLCData(ip, tags)
    while True:
        sleep(1)
        # Update values from PLC
        plc_data.update()

        # Prepare data for tabular display
        table_data = []
        for tag in tags:
            key = tag["key"]
            tag_name = tag["tag_name"]
            value = plc_data.get_tags().get(tag_name, "N/A")
            table_data.append([key, tag_name, value])

        # Print in tabular format
        print(tabulate(table_data, headers=["Key", "Tag Name", "Value"], tablefmt="grid"))
        pass