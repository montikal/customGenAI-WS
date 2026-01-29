Custom Gen-AI workshop: \
 \
installation steps \
$ python -m venv .venv \
$ .venv/Scripts/activate.ps1 #in powershell \
$ pip install -r requirement.txt \
$ uvicorn app.main:app \

# Open browser with \n
http://localhost:8000/ui/

Note: to run neo4j in docker or desktop
* check username and password to align
* view knowledge graph in http://localhost:7474/browser/
