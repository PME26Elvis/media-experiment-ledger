# 04 — Media API Automation Specification

## 1. Scope

API Automation is an optional module for generating and downloading image/video media through supported providers. Agnes is the initial provider because the repository already contains a working harvester and real longitudinal run data.

The app implementation must preserve useful existing behavior—separate image/video phases, prompt files, intervals, polling, target success counts, error classification and atomic state—but replace script-only controls with a richer, durable and inspectable product.

API Automation must not be required to use Atlas, Detection Studio or sample data.

## 2. Provider architecture

### 2.1 Provider adapter

Every provider implements a versioned adapter interface:

```ts
interface MediaProviderAdapter {
  id: string
  displayName: string
  adapterVersion: string
  capabilities(): Promise<ProviderCapabilities>
  validateCredential(profileRef: string): Promise<CredentialTestResult>
  validateConfig(config: ProviderRunConfig): Promise<ValidationReport>
  submitImage(request: ImageGenerationRequest): Promise<SubmissionResult>
  submitVideo(request: VideoGenerationRequest): Promise<SubmissionResult>
  poll?(submission: SubmissionRef): Promise<PollResult>
  cancelRemote?(submission: SubmissionRef): Promise<RemoteCancelResult>
  classifyError(error: unknown): ClassifiedProviderError
  resolveOutputs(result: ProviderResult): Promise<OutputDescriptor[]>
}
```

The renderer never calls this adapter directly. A supervised backend service owns credentials, networking and durable request state.

### 2.2 Provider manifest

A provider manifest declares:

- adapter ID/version;
- display name and documentation URL;
- supported media types;
- supported models;
- request fields and validation constraints;
- synchronous/asynchronous execution mode;
- polling behavior;
- rate-limit metadata if known;
- output forms: URL/base64/provider storage;
- cancellation support;
- credential fields;
- data-retention notice;
- config schema version.

Capabilities may be refreshed but a run stores an immutable snapshot so future provider changes do not rewrite historical meaning.

## 3. Agnes initial integration

### 3.1 Existing baseline to preserve

The current repository config uses:

- `AGNES_API_KEY` environment variable;
- base URL `https://apihub.agnes-ai.com`;
- image model configuration;
- video model configuration;
- separate image and video prompt JSONL files;
- target success counts;
- create intervals;
- video polling interval and timeout;
- optional width/height;
- seed range;
- negative prompt;
- stop policies for quota/payment, rate limit and server busy;
- maximum consecutive errors;
- output download toggle;
- atomic state-file replacement.

The app must import this YAML shape through a compatibility importer, but the app-native config schema is richer and versioned.

### 3.2 Endpoint abstraction

Initial Agnes behavior is expected to include:

- image submission;
- video submission;
- asynchronous video polling when required;
- output URL extraction;
- download and media verification.

Exact endpoints and response fields must be isolated in the adapter and covered by recorded redacted fixtures. UI code must not assume fields such as `data[0].url` or `video_url`.

### 3.3 Provider-change safety

When Agnes changes models, limits or response schema:

- capability refresh creates a new snapshot;
- existing presets remain readable;
- invalid/deprecated fields are highlighted;
- running jobs continue using stored adapter/config version when possible;
- incompatible jobs pause with a migration explanation rather than sending guessed requests.

## 4. Credential management

### 4.1 Credential profiles

Users may create multiple Agnes profiles, for example personal, test or quota-separated accounts.

Profile fields:

- stable profile ID;
- display name;
- provider ID;
- encrypted API key;
- optional non-secret account note;
- created/updated time;
- last successful validation time;
- last failure category;
- masked fingerprint such as final four characters;
- usage policy assignment;
- enabled/disabled state.

### 4.2 Credential UI

The credential screen must provide:

- create/edit/delete profile;
- paste/import from `.env`;
- reveal containing `.env` folder for file-backed mode;
- temporary reveal/copy with warning;
- test connection;
- select default profile;
- inspect which presets reference the profile;
- rotate/replace key without editing dependent configs;
- export profile metadata without secret;
- explicit secret-bearing `.env` export flow.

### 4.3 Multiple-key scheduling

The system may support multiple credentials for one provider, but automatic key rotation is security/cost-sensitive.

Provisional modes:

- fixed profile;
- ordered fallback after terminal quota/permission classification;
- round-robin per successful request;
- weighted profile selection;
- disabled profile quarantine after repeated auth failures.

The run review page must show the selected policy. Hidden automatic key switching is prohibited.

## 5. Prompt and task inputs

### 5.1 Supported sources

- app editor;
- JSONL prompt file;
- CSV;
- JSON;
- clipboard paste;
- imported repository-compatible prompt files;
- future generated task sets.

### 5.2 Canonical task record

```json
{
  "taskId": "stable-user-or-generated-id",
  "mediaType": "image",
  "prompt": "...",
  "negativePrompt": "...",
  "model": "provider-model-id",
  "parameters": {},
  "tags": [],
  "repeatCount": 1,
  "enabled": true,
  "source": {}
}
```

IDs must be unique within a run. Duplicate prompts may be intentional and are not deduplicated unless the user selects that policy.

### 5.3 Task validation

Validate:

- required prompt/ID;
- duplicate ID;
- provider model availability;
- parameter range;
- unsupported media type;
- expected request count;
- missing output path;
- repeat count explosion;
- invalid seed range;
- file encoding/parse failures.

A validation preview shows valid, warning and blocked task counts.

## 6. Automation configuration model

### 6.1 General settings

- run name;
- provider and credential profile;
- enabled media phases;
- task source;
- output paths;
- raw response retention;
- output download behavior;
- timezone for display only; all persisted timestamps also include UTC;
- start mode: now/manual schedule;
- priority;
- notes/tags.

### 6.2 Request pacing

Separate settings per media type:

- minimum interval between submissions;
- randomized jitter range;
- maximum concurrent submissions;
- maximum concurrent downloads;
- maximum concurrent polls;
- poll interval;
- poll timeout;
- provider Retry-After respect;
- global provider rate bucket;
- per-credential rate bucket;
- optional quiet hours;
- adaptive slowdown policy.

The GUI shows effective maximum request rate and warns when interval/concurrency combinations conflict.

### 6.3 Retry policy

Per error class:

- maximum attempts;
- base delay;
- backoff: fixed/linear/exponential;
- maximum delay;
- jitter;
- respect provider Retry-After;
- retry same credential or change profile;
- retry same request ID/idempotency key;
- terminal/pausing behavior.

Initial error taxonomy:

- authentication/permission;
- bad request/configuration;
- quota/payment;
- rate limit;
- duplicate/conflict;
- timeout/network;
- server busy/upstream timeout;
- polling timeout;
- download failure;
- media verification failure;
- unknown provider error.

### 6.4 Stop conditions

The user can define any combination:

- target successful images;
- target successful videos;
- all enabled tasks completed;
- maximum submitted requests;
- maximum total attempts;
- maximum consecutive errors;
- maximum errors by class;
- quota/payment error;
- authentication error;
- rate-limit event count;
- server-busy duration;
- wall-clock deadline;
- maximum run duration;
- maximum downloaded bytes;
- estimated/recorded spend threshold when provider pricing data exists;
- minimum disk free space;
- user-defined manual stop.

Stop actions:

- pause for review;
- stop current media phase and continue other phase;
- stop entire run;
- enter cooldown and retry;
- switch credential according to explicit policy.

### 6.5 Circuit breaker

A provider/credential circuit breaker prevents rapid repeated failures.

States:

- closed: normal;
- open: requests blocked until cooldown/manual review;
- half-open: one or limited probe requests;
- disabled: user override with warning.

Breaker state is persisted and visible.

## 7. Scheduling

### 7.1 Local scheduling

Supported:

- start now;
- start at date/time;
- recurring schedule provisional;
- run only within allowed hours;
- pause outside allowed hours;
- continue after app restart if user enabled background launch.

The app must explain that desktop scheduling requires the machine and app/agent to be running unless a platform service is installed in a later milestone.

### 7.2 Sleep and shutdown

Provisional behavior:

- active jobs can request OS sleep prevention while a submission/download is in flight;
- user can choose allow sleep and recover later;
- app shutdown dialog offers keep running in tray, pause and quit, or force quit;
- forced termination leaves durable checkpoints.

## 8. Run lifecycle and durable state

### 8.1 States

- draft;
- validating;
- queued;
- waiting-for-schedule;
- running;
- cooling-down;
- pausing;
- paused;
- stopping;
- stopped;
- cancelling-remote provisional;
- failed;
- recoverable;
- completed;
- completed-with-errors.

### 8.2 Request record

Every attempt records:

- request UUID;
- task ID;
- media type;
- provider/model;
- credential profile ID, not secret;
- configuration snapshot hash;
- submission time;
- attempt number;
- idempotency key when supported;
- sanitized request summary;
- HTTP/provider status;
- classified error;
- Retry-After;
- provider submission/job ID;
- poll history summary;
- completion time;
- output descriptors;
- download/verification status;
- response archive reference;
- next retry time.

### 8.3 Checkpoint rules

A task is successful only after:

1. provider reports success;
2. output descriptor resolves;
3. requested media is downloaded if download is enabled;
4. file is non-empty;
5. content type/extension is plausible;
6. decode verification passes according to media type;
7. hash and metadata are stored;
8. durable state commits.

A remote success with failed download is not counted as a fully archived success, though UI distinguishes provider success from archive failure.

### 8.4 Recovery

On restart:

- submitted asynchronous jobs are polled again;
- pending retries retain scheduled time;
- completed verified tasks are skipped;
- download temp files resume where HTTP range and provider URL allow, otherwise restart safely;
- expired output URLs trigger provider-result refresh if possible;
- ambiguous request state is surfaced, not blindly resubmitted;
- user may mark an ambiguous item for safe manual retry.

## 9. Output and provenance

Suggested run layout:

```text
media/generated/<run-id>/
├─ images/
├─ videos/
├─ raw-responses/
├─ manifests/
│  ├─ run.json
│  ├─ tasks.jsonl
│  ├─ attempts.jsonl
│  └─ outputs.jsonl
└─ logs/
```

The database is canonical for app operation; JSON/JSONL manifests are exportable evidence and interoperability surfaces.

Filename policy:

- stable task ID prefix;
- attempt/variant information where needed;
- sanitized short descriptor optional;
- original extension derived from verified content;
- collision-safe;
- no secret or full prompt text in filename by default.

## 10. GUI specification

### 10.1 Automation landing page

Cards:

- active runs;
- recoverable runs;
- provider status;
- recent success/error totals;
- credential warnings;
- output storage;
- create run primary action.

### 10.2 Run creation wizard

Steps:

1. Provider and credential.
2. Media types and models.
3. Task input.
4. Output paths.
5. Pacing and concurrency.
6. Retry and circuit-breaker policy.
7. Stop/budget policy.
8. Validation and request estimate.
9. Final review and start/save preset.

Each step uses responsive `v-row`/`v-col`, meaningful icons/colors, `v-hover` presets/cards and transitions between steps.

### 10.3 Live run page

Tabs:

- Overview;
- Image queue;
- Video queue;
- Requests;
- Outputs;
- Errors;
- Logs;
- Effective config.

Overview includes:

- progress by phase;
- success/provider-success/archive-success distinction;
- current rate;
- cooldown state;
- next scheduled action;
- active credential profile;
- disk usage;
- pause/stop controls.

### 10.4 Error review

Filter by class, task, credential and retryability. Bulk actions:

- retry selected;
- retry with changed profile;
- edit-and-retry bad requests;
- ignore/mark resolved;
- export error report.

## 11. Config interoperability

The app imports the existing `agnes_media_config.yaml` schema and prompt JSONL files.

Import mapping includes:

- timezone;
- base URL;
- output/state/log paths;
- HTTP timeouts;
- image/video enabled;
- model;
- prompt file;
- target success;
- create/poll intervals;
- video frame/size/seed/negative prompt;
- stop flags;
- consecutive errors;
- download behavior.

Unsupported or ambiguous existing fields remain visible in an import report. The original file is not rewritten unless the user explicitly exports back to it.

## 12. Security and privacy

- credentials remain backend-only;
- authorization headers are redacted;
- response bodies are sanitized before logs;
- signed output URLs may be sensitive and can be redacted after download;
- base URL changes are expert-only and display phishing/exfiltration warning;
- provider adapter restricts hosts by default;
- imported configs cannot point to arbitrary executable adapters;
- raw response retention is opt-in or clearly disclosed;
- prompt and response data are never uploaded elsewhere by the app.

## 13. Performance

- renderer receives aggregated progress at bounded frequency, not one reactive update per network chunk/poll;
- requests and logs use paginated DB queries;
- output thumbnails are generated asynchronously;
- thousands of task rows use virtualization;
- raw response viewer loads on demand;
- network worker limits connection pool and queued in-memory bodies;
- large downloads stream to disk rather than buffering whole files.

## 14. Acceptance criteria

- user can complete a sample-data workflow without any credential;
- user can import current Agnes YAML/JSONL configuration;
- secrets are encrypted and excluded from normal exports/logs;
- image and video outputs can use independent paths and policies;
- rate/concurrency GUI shows effective behavior;
- stop conditions work per phase and globally;
- Retry-After and classified errors affect scheduling deterministically;
- app restart resumes submitted video polls and pending downloads;
- verified successes are not repeated;
- ambiguous submissions are not blindly duplicated;
- every archived output has checksum and request provenance;
- run config, state and evidence can be exported;
- UI remains responsive with at least 10,000 task records.