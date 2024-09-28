
## get API keys and put in .env

- IDEOGRAM_API_KEY go to https://ideogram.ai/manage-api you'll have to put your credit card on file...
- OPENAI_API_KEY go to https://platform.openai.com/api-keys
- LUMAAI_API_KEY go to https://lumalabs.ai/dream-machine/api/keys
- AIRTABLE_API_KEY go to https://discord.com/channels/822583790773862470/1287822195527127145/1289696842845655207

## Running luma.ipynb in VSCode

Note: all dependencies are now located inside a cell.

```python
!pip install openai
!pip install requests
!pip install tweet-capture
!pip install lumaai
!pip install pyairtable

from dotenv import load_dotenv
# Load environment variables
load_dotenv()
```

To run the `luma.ipynb` Jupyter notebook inside Visual Studio Code (VSCode), follow these steps:

1. **Install VSCode**:
    If you haven't already, download and install Visual Studio Code from [here](https://code.visualstudio.com/).

2. **Install Python Extension**:
    Open VSCode and install the Python extension by Microsoft. You can find it in the Extensions view by searching for "Python".

3. **Open the Project Folder**:
    Open the `luma-hack` project folder in VSCode.

4. **Install Jupyter**:
    Ensure you have Jupyter installed in your environment. You can install it using UV:
    ```sh
    uv run pip install jupyter
    ```

5. **Open luma.ipynb**:
    Locate the `luma.ipynb` file in the Explorer view and open it. VSCode will automatically open it in the Jupyter Notebook interface.

6. **Select Python Interpreter**:
    Make sure to select the correct Python interpreter that has the necessary dependencies installed. You can do this by clicking on the interpreter in the bottom-left corner of VSCode and selecting the appropriate environment.

7. **Run Cells**:
    You can now run the cells in the notebook by clicking the "Run" button at the top of each cell or by using the `Shift + Enter` shortcut.

By following these steps, you should be able to run and interact with the `luma.ipynb` notebook inside VSCode seamlessly.
