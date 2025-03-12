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
        try:
            for tag in self.tags:
                
                tag_name = tag["tag_name"]  # Extract tag name
                response = self.plc.Read(tag_name)  # Read value from PLC
                [tg, temp, status] = str(response).split(' ')
                self.tag_values[tag["key"]] = temp  # Store the value
        except Exception as e:
            print('error in updating', e)
        
            
    def get_tags(self):
        return self.tag_values  # Return the latest tag values
    


if __name__ == "__main__":
    ip = "192.168.11.1"
    tags = [
        {"src": "heater", "key": "13", "tag_name": "FROM_MACHINE_4C_PLC[43]"},
        {"src": "heater", "key": "12", "tag_name": "FROM_MACHINE_4C_PLC[42]"},
        {"src": "heater", "key": "11", "tag_name": "FROM_MACHINE_4C_PLC[41]"},
        {"src": "heater", "key": "10", "tag_name": "FROM_MACHINE_4C_PLC[39]"},
        {"src": "heater",  "key": "9", "tag_name": "FROM_MACHINE_4C_PLC[38]"},
        {"src": "heater",  "key": "8", "tag_name": "FROM_MACHINE_4C_PLC[37]"},
        {"src": "heater",  "key": "7", "tag_name": "FROM_MACHINE_4C_PLC[36]"},
        {"src": "heater", "key": "26", "tag_name": "FROM_MACHINE_4C_PLC[56]"},
        {"src": "heater", "key": "25", "tag_name": "FROM_MACHINE_4C_PLC[55]"},
        {"src": "heater", "key": "24", "tag_name": "FROM_MACHINE_4C_PLC[54]"},
        {"src": "heater", "key": "23", "tag_name": "FROM_MACHINE_4C_PLC[53]"},
        {"src": "heater", "key": "22", "tag_name": "FROM_MACHINE_4C_PLC[52]"},
        {"src": "heater", "key": "21", "tag_name": "FROM_MACHINE_4C_PLC[51]"},
        {"src": "heater", "key": "20", "tag_name": "FROM_MACHINE_4C_PLC[50]"},
        {"src": "main-motor", "key": "motor", "tag_name": "FROM_MACHINE_4C_PLC[64]"},
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