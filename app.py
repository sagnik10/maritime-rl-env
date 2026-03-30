import gradio as gr 
 
def status(): 
    return "Maritime RL Environment is running" 
 
demo = gr.Interface(fn=status, inputs=[], outputs="text", title="Maritime RL Environment") 
demo.launch(server_name="0.0.0.0", server_port=7860) 
