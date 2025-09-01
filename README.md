## Deployment (Railway)

### Quick Deploy
1. Ensure repository contains added `Dockerfile` and `backend/wsgi.py` (already included).
2. Push changes to your default branch.
3. In Railway: New Project -> Deploy from GitHub -> select this repo.
4. Railway auto-detects the Dockerfile and builds multi-stage image.
5. After deploy, open the URL: `/api/health` should return JSON; root serves the React build.

### Local Docker Test
```
docker build -t pokemon-game .
docker run -p 8000:8000 pokemon-game
```
Visit http://localhost:8000

### Environment Notes
In-memory state (lobbies, games) resets on redeploy or container restart. For persistence, add Redis and refactor storage.

### Scaling
Single process (3 Gunicorn workers). Horizontal scaling would require shared state (Redis) + possibly WebSockets/SSE for realtime.

# Flask-App
My personal template for creating for flask web application monorepos. Includes backend and frontend frameworks.

**OPERATING SYSTEMS:** Much of these instructions were done in windows. That said, please let me know if there's any discrepancies setting up for another operating system.

**IMPORTANT**:For the setup below, everything was done via a bash terminal.


<br/>


## Development Stack

**Design & Planning**
- INSERT LINKS TO DOCUMENTATION

**Prerequisites**
- [Git Bash](https://git-scm.com/downloads)
- [Python 3.12.8](python.org/downloads/release/python-3128)
- [Node v20.12.2](nodejs.org/en/blog/release/v20.12.2)
- [Backend .env Download (n/a)]()
- [Frontend .env Download (n/a)]()


<br/>


## Python Backend Setup
For backend development, we'll be using the Flask Python framework. To set that up along with everything else we'll need, follow the instructions below. ENSURE YOUR IDE IS ON PYTHON 3.12.8.

CD into the backend folder and setup the environment by executing the following.
```bash
cd ./backend
python -m venv "./venv"
```
At this point, your environment should be setup. This is the environment where everything should be ran to ensure consistancy and isolation. When you need to activate your virtual environment, execute the following.
```shell
# For Windows systems
source venv/Scripts/activate
```
or if on MACOS or other Unix systems...
```bash
# For MACOS/Unix systems
source venv/bin/activate
```

For the first time setup, or when new packages are added to the `requirements.txt` file, use the following command to install all required Python packages.
```bash
pip install -r requirements.txt
```

Once all packages are installed, you should be able to start up the backend server via the following command.
```bash
python ./app.py
```


<br/>



## Frontend Setup
For the frontend, we'll Next.js for that we'll need Node. To set that up along with everything else we'll need, follow the instructions below.

Once you have Node.js installed, run the following commands to install the required packages.
```bash
cd ./frontend
npm install
```
Once installed, you should be able to start the development server with the following.
```bash
npm run dev
```

View the webpage at [http://localhost:3000](http://localhost:3000)

Node, this project uses next/font to automatically optimize and load Geist, a new font family for Vercel.



<br/>



## Project Compilation
Compile the entire project (frontend build + backend executable) using the existing PyInstaller spec.

**Build Frontend**
Build the frontend (Vite outputs to `frontend/dist`).
```bash
cd frontend
npm ci
npm run build
```
Install backend deps and PyInstaller (first time only).
```bash
cd ../backend
pip install -r requirements.txt
pip install pyinstaller
```

**Build .exe**
Using the provided spec file (ensures frontend `dist` and OR-Tools libs are bundled correctly), run the following.
```bash
pyinstaller --clean --noconfirm PROJECT_NAME.spec
```
Run the generated executable:
```bash
./dist/PROJECT_NAME/PROJECT_NAME.exe
```
The app will start Flask on `http://localhost:8080` and open your browser.



<br/>



## Regenerating / updating the spec (only if you need to)
If you add entry points or want a fresh spec:
```bash
pyi-makespec app.py --name PROJECT_NAME --add-data "../frontend/dist;frontend/dist"
```
Then edit the generated `.spec` similarly to the committed one (adding OR-Tools `.libs` and the frontend Tree) and rebuild with the `pyinstaller --clean --noconfirm PROJECT_NAME.spec` command above.



<br/>



## Cleaning the  Build Slate
Remove build artifacts if you encounter issues:
```bash
rm -rf frontend/dist
rm -rf backend/build backend/dist backend/__pycache__
```
(Keep `PROJECT_NAME.spec` unless you intentionally want to regenerate it.)



<br/>
<br/>



# Project Tech Stack

**Frontend Stack**
- NextJS
- Tailwind CSS
- ...more...

**Backend Stack**
- Python 3.12.8
- Flask
- ...more...