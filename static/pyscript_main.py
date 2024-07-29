from pyscript import document, fetch, when
#import test

@when("click", "#execute")
async def execute(event):
    input_text = document.querySelector("#command")
    command = input_text.value
    output_div = document.querySelector("#output")
    text = await fetch(f"/cmd/{command}").text()
    output_div.innerText = f"your command was {command}, response was {text}"
