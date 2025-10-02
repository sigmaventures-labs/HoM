\#\#\# Quick guide: reuse \`paycom\_async\` in another Cursor project

\- Prereqs  
  \- \*\*Python\*\*: 3.11+  
  \- Have this repo available on your machine at \`"/Users/client/Documents/Dev/MaX"\`

\#\#\# 1\) Add the dependency (local path)  
\- pip (recommended for quick trial):  
\`\`\`bash  
pip install \-e /Users/client/Documents/Dev/MaX/libs/paycom\_async  
\`\`\`  
\- requirements.txt (so teammates can replicate locally on macOS paths):  
\`\`\`text  
\-e file:///Users/client/Documents/Dev/MaX/libs/paycom\_async  
\`\`\`  
\- Poetry:  
\`\`\`bash  
poetry add \--path /Users/client/Documents/Dev/MaX/libs/paycom\_async  
\`\`\`

\#\#\# 2\) Configure environment  
\- Set your credentials and base URL (use your Replit mock URL or production later):  
\`\`\`bash  
export PAYCOM\_SID="your\_sid"  
export PAYCOM\_TOKEN="your\_token"  
export PAYCOM\_BASE\_URL="https://your-replit-subdomain.replit.app"  
\`\`\`  

\#\#\#\# Ingestion order (important)
\- Sync employees first, then time entries.
\- Reason: time entries link to employees via \`external\_id\`; running time entries first can cause partial/failed ingestion if employees aren’t present.

\#\#\# 3\) Use in code  
\`\`\`python  
import asyncio  
from datetime import date  
from paycom\_async import PaycomConnector

async def main():  
    client \= PaycomConnector(sid="your\_sid", token="your\_token")  \# or read from env  
    employees \= await client.fetch\_employees(active\_only=True)  
    print(f"employees={len(employees)}")

    count \= 0  
    async for tc in client.fetch\_timecards(start\_date=date(2025,1,1), end\_date=date(2025,1,31)):  
        count \+= 1  
    print(f"timecards={count}")

asyncio.run(main())  
\`\`\`

\#\#\# 4\) Optional: run against the local mock (instead of Replit)  
\`\`\`bash  
export PAYCOM\_BASE\_URL=http://127.0.0.1:9000  
uvicorn mock.paycom\_mock:app \--port 9000 \--reload  
\`\`\`

\#\#\# 5\) CI and portability notes  
\- Local path installs won’t work in CI or on other machines without the same path. When you’re ready:  
  \- Switch to a Git dependency:  
    \- pip: \`pip install git+ssh://git@github.com/OWNER/paycom-async.git@v0.1.0\`  
    \- Poetry: \`paycom-async \= { git \= "ssh://git@github.com/OWNER/paycom-async.git", tag \= "v0.1.0" }\`  
  \- Or publish to a private registry and depend by version.

\#\#\# 6\) Upgrading during trial  
\- Pull latest changes in the MaX repo, then re-run:  
\`\`\`bash  
pip install \-e /Users/client/Documents/Dev/MaX/libs/paycom\_async  
\`\`\`  
