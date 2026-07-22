import { app } from 'electron'
import { access } from 'node:fs/promises'
import { join } from 'node:path'
import { spawn } from 'node:child_process'
import { createInterface } from 'node:readline'

export interface EngineEvent { type:'progress'|'result'|'error'|'log'; stage?:string; progress?:number; completed?:number; total?:number; data?:Record<string,unknown>; message?:string }

export function engineRoot(): string { return app.isPackaged ? join(process.resourcesPath,'engine') : join(app.getAppPath(),'engine') }
export async function engineReady(): Promise<boolean> { try { await access(join(engineRoot(),'mel_engine','__main__.py')); return true } catch { return false } }

function pythonCommand(): string {
  if (process.env.MEL_PYTHON) return process.env.MEL_PYTHON
  const packaged=process.platform==='win32'?join(process.resourcesPath,'python','python.exe'):join(process.resourcesPath,'python','bin','python3')
  return app.isPackaged?packaged:(process.platform==='win32'?'python':'python3')
}

export function runEngine(payload:Record<string,unknown>,onEvent:(event:EngineEvent)=>void,signal:AbortSignal,environment:Record<string,string>={}):Promise<Record<string,unknown>> {
  return new Promise((resolve,reject)=>{
    const child=spawn(pythonCommand(),['-m','mel_engine'],{cwd:engineRoot(),env:{...process.env,...environment,PYTHONPATH:engineRoot()},stdio:['pipe','pipe','pipe'],windowsHide:true,shell:false})
    let finalResult:Record<string,unknown>|undefined
    const stdout=createInterface({input:child.stdout})
    stdout.on('line',(line)=>{try{const event=JSON.parse(line) as EngineEvent; onEvent(event); if(event.type==='result')finalResult=event.data??{}; if(event.type==='error')reject(new Error(event.message??'Engine error'))}catch{onEvent({type:'log',message:line})}})
    child.stderr.on('data',(chunk)=>onEvent({type:'log',message:String(chunk).trim()}))
    child.on('error',reject)
    child.on('exit',(code)=>code===0?resolve(finalResult??{}):reject(new Error(`Engine exited with code ${code}`)))
    signal.addEventListener('abort',()=>child.kill(),{once:true})
    child.stdin.write(`${JSON.stringify(payload)}\n`); child.stdin.end()
  })
}
