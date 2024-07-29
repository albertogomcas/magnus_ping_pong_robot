from pyscript import document
#import test
def execute(event):
    input_text = document.querySelector("#command")
    command = input_text.value
    output_div = document.querySelector("#output")
    output_div.innerText = f"your command was {command}"

    if command == "on":
        pass
        #test.on()

    if command == "off":
        pass
        #test.off()