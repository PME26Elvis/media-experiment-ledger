import { randomUUID } from 'node:crypto'
import type { CreateJobRequest, JobRecord } from '../shared/contracts'
import { runEngine } from './engine'
import { StudioDatabase } from './database'
import { SecretStore } from './secret-store'

export class JobManager {
  private controllers=new Map<string,AbortController>()
  constructor(private readonly db:StudioDatabase,private readonly secrets:SecretStore){}
  list():JobRecord[]{return this.db.listJobs()}
  create(request:CreateJobRequest):JobRecord{const now=new Date().toISOString();const job:JobRecord={id:randomUUID(),kind:request.kind,title:request.title,status:'queued',stage:'queued',progress:0,completedItems:0,totalItems:0,config:request.config,createdAt:now,updatedAt:now};this.db.upsertJob(job);void this.start(job);return job}
  async start(job:JobRecord):Promise<void>{const controller=new AbortController();this.controllers.set(job.id,controller);this.save({...job,status:'running',stage:'starting'});try{const profileId=typeof job.config.credential_profile_id==='string'?job.config.credential_profile_id:undefined;const environment=await this.secrets.resolveEnvironment(profileId);const output=await runEngine({operation:job.kind,job_id:job.id,...job.config},(event)=>{const current=this.db.getJob(job.id)??job;if(event.type==='progress')this.save({...current,status:'running',stage:event.stage??current.stage,progress:Math.max(0,Math.min(100,event.progress??current.progress)),completedItems:event.completed??current.completedItems,totalItems:event.total??current.totalItems})},controller.signal,environment);const current=this.db.getJob(job.id)??job;this.save({...current,status:'completed',stage:'verified',progress:100,output})}catch(error){const current=this.db.getJob(job.id)??job;const cancelled=controller.signal.aborted;this.save({...current,status:cancelled?'cancelled':'recoverable',stage:cancelled?'cancelled':'failed',error:error instanceof Error?error.message:String(error)})}finally{this.controllers.delete(job.id)}}
  control(id:string,action:'pause'|'resume'|'cancel'):JobRecord{const job=this.db.getJob(id);if(!job)throw new Error('Job not found');if(action==='cancel'){this.controllers.get(id)?.abort();const next={...job,status:'cancelling' as const,stage:'cancelling'};this.save(next);return next}if(action==='pause'){this.controllers.get(id)?.abort();const next={...job,status:'paused' as const,stage:'paused'};this.save(next);return next}if(job.status==='paused'||job.status==='recoverable'){const next={...job,status:'queued' as const,stage:'queued',error:undefined};this.save(next);void this.start(next);return next}return job}
  private save(job:JobRecord):void{this.db.upsertJob({...job,updatedAt:new Date().toISOString()})}
}
