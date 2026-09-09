"""Read-only compile preflight; root still performs the actual Unity import/build."""
from pathlib import Path
import hashlib,json,subprocess
R=Path('/home/teknetik/code/ao2');U=Path('/home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Data');O=R/'art/quality_20260908/platform-terminals';F=U/'UnityReferenceAssemblies/unity-4.8-api'
refs=list(F.glob('*.dll'))+list((F/'Facades').glob('*.dll'))+[p for p in(U/'Managed/UnityEngine').glob('Unity*.dll')if p.name not in['UnityEngine.dll','UnityEditor.dll']]+[U/'Managed/Newtonsoft.Json.dll']+[R/'unity/AthenHill/Library/ScriptAssemblies'/n for n in['Assembly-CSharp.dll','Assembly-CSharp-Editor.dll','AthenHill.Runtime.dll']]
source=O/'PlatformTerminalPass.cs';args=['-nologo','-target:library','-langversion:9','-nostdlib+','-out:/tmp/ward-platform-terminal-syntax.dll']+['-r:'+str(p)for p in refs]+[str(source)]
process=subprocess.run([str(U/'NetCoreRuntime/dotnet'),str(U/'DotNetSdk/sdk/8.0.318/Roslyn/bincore/csc.dll'),*args],text=True,capture_output=True)
report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'exit_code':process.returncode,'stdout':process.stdout,'stderr':process.stderr,'note':'Read-only compile using Unity 6000.6 reference assemblies, managed/editor modules and current project assemblies. Does not import or mutate the Unity scene.'}
(O/'compiler-check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(process.returncode)
