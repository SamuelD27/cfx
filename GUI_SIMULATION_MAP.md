# CharForgex GUI Simulation Map

**Generated:** 2025-12-23
**Purpose:** Document expected vs actual GUI behavior to identify "dead click" issues

---

## Table of Contents

1. [Action Inventory](#action-inventory)
2. [Settings Screen](#settings-screen)
3. [Media Library Screen](#media-library-screen)
4. [Datasets Screen](#datasets-screen)
5. [Characters Screen](#characters-screen)
6. [Create Character Screen](#create-character-screen)
7. [Training Screen](#training-screen)
8. [Inference Screen](#inference-screen)
9. [Identified Issues Summary](#identified-issues-summary)
10. [Proposed Fixes](#proposed-fixes)

---

## Action Inventory

| Action ID | Screen | Control Label | Expected Outcome |
|-----------|--------|--------------|------------------|
| GUI-ACT-SETTINGS-SAVE | Settings | Save Configuration | Save env vars to backend |
| GUI-ACT-SETTINGS-TEST | Settings | Test Configuration | Validate API keys |
| GUI-ACT-SETTINGS-RESET | Settings | Reset | Reload saved settings |
| GUI-ACT-MEDIA-UPLOAD | Media Library | Upload Images | Upload files to backend |
| GUI-ACT-MEDIA-DELETE | Media Library | Delete (trash icon) | Delete file from backend |
| GUI-ACT-MEDIA-CREATE-DS | Media Library | Create Dataset | Open dataset creation modal |
| GUI-ACT-MEDIA-VIEW | Media Library | Image click | Open image detail modal |
| GUI-ACT-DS-VIEW | Datasets | Dataset card click | Open dataset detail modal |
| GUI-ACT-DS-EDIT | Datasets | Edit button | Open edit modal |
| GUI-ACT-DS-DELETE | Datasets | Delete button | Delete dataset |
| GUI-ACT-DS-TRAIN | Datasets | Train button | Navigate to create character |
| GUI-ACT-DS-CREATE | DatasetModal | Create Dataset | Submit dataset to backend |
| GUI-ACT-CHAR-CREATE-NAV | Characters | Create Character | Navigate to /characters/create |
| GUI-ACT-CHAR-VIEW | Characters | Character card | Navigate to character detail |
| GUI-ACT-CHAR-START-TRAIN | Characters | Start Training | Start training job |
| GUI-ACT-CHAR-DELETE | Characters | Delete | Delete character |
| GUI-ACT-CREATECHAR-SUBMIT | Create Character | Create Character | Create character record |
| GUI-ACT-CREATECHAR-IMGSELECT | Create Character | Choose from Library | Open media selection modal |
| GUI-ACT-CREATECHAR-UPLOAD | Create Character | Upload image | Upload reference image |
| GUI-ACT-INF-GENERATE | Inference | Generate Images | Start inference job |
| GUI-ACT-INF-PRESET | Inference | Preset buttons | Apply preset config |
| GUI-ACT-TRAIN-VIEWLOGS | Training | View Logs | Show training logs modal |

---

## Settings Screen

### GUI-ACT-SETTINGS-SAVE

**User Intent:** Save environment configuration (API keys, paths)

**Expected Chain:**
1. UI Event: Form submit (`@submit.prevent="saveEnvironmentSettings"`)
2. Frontend function: `saveEnvironmentSettings()` in `SettingsView.vue:196`
3. State changes: `isSaving = true`, button disabled
4. Network request: `POST /api/settings/environment` with body `{ HF_TOKEN, HF_HOME, ... }`
5. Backend endpoint: `settings.py:@router.post("/environment")` mounted at `/api/settings`
6. Backend service: `save_environment_settings()` - saves to database
7. Response: `{ HF_TOKEN, HF_HOME, ... }` (saved values)
8. Post-response: `isSaving = false`, toast success

**Verification:**
- [x] Handler bound: `@submit.prevent="saveEnvironmentSettings"` (line 27)
- [x] Function exists: `saveEnvironmentSettings()` (line 196-206)
- [x] API call: `settingsApi.saveEnvironment(envSettings.value)` (line 199)
- [x] Backend route exists: `@router.post("/environment")` in `settings.py`
- [x] Backend uses `get_current_user_optional` (FIXED in previous session)
- [x] Error handling: try/catch with toast.error (line 201-202)

**Status:** ✅ WORKING (after auth fix)

---

### GUI-ACT-SETTINGS-TEST

**User Intent:** Test if API keys are valid

**Expected Chain:**
1. UI Event: Button click `@click="testEnvironment"`
2. Frontend function: `testEnvironment()` in `SettingsView.vue:208`
3. State changes: `isTestingEnv = true`
4. Network request: `GET /api/settings/test-environment`
5. Backend endpoint: `settings.py:@router.post("/test-environment")`
6. Response: `{ HF_TOKEN: { valid, message }, ... }`
7. Post-response: Update `testResults`, show toast

**Verification:**
- [x] Handler bound: `@click="testEnvironment"` (line 21)
- [x] Function exists: `testEnvironment()` (line 208-227)
- [x] API call: `settingsApi.testEnvironment()` (line 211)
- [!] **MISMATCH:** Frontend calls `GET` but backend is `@router.post`

**Breakpoint:** Frontend api.ts line 219-220 calls `api.get('/settings/test-environment')` but backend `settings.py` declares `@router.post("/test-environment")`

**Status:** ❌ BROKEN - HTTP method mismatch

---

## Media Library Screen

### GUI-ACT-MEDIA-UPLOAD

**User Intent:** Upload image files

**Expected Chain:**
1. UI Event: File input change `@change="handleFileSelect"`
2. Frontend function: `handleFileSelect()` → `uploadFiles()`
3. Network request: `POST /api/media/upload` (multipart/form-data)
4. Backend endpoint: `media.py:@router.post("/upload")`
5. Response: MediaResponse with file_url
6. Post-response: Add to mediaFiles array, toast success

**Verification:**
- [x] Handler bound: `@change="handleFileSelect"` (line 37)
- [x] Upload function: `uploadFiles()` (line 273-311)
- [x] API call: `mediaApi.upload(file)` (line 292)
- [x] Backend route: `@router.post("/upload")` in `media.py:87`
- [x] Uses `get_current_user_optional` (FIXED)

**Status:** ✅ WORKING

---

### GUI-ACT-MEDIA-CREATE-DS

**User Intent:** Open dataset creation modal

**Expected Chain:**
1. UI Event: Button click `@click="showDatasetModal = true"`
2. Frontend state: `showDatasetModal = true`
3. Modal rendered: `<DatasetModal v-if="showDatasetModal" :files="files" ...>`

**Verification:**
- [x] Handler bound: `@click="showDatasetModal = true"` (line 16)
- [!] **BUG FOUND:** Line 204 passes `:files="files"` but `files` is UNDEFINED
- [x] Correct variable is `mediaFiles`

**Breakpoint:** `MediaView.vue:204` passes undefined `files` prop instead of `mediaFiles`

**Status:** ❌ BROKEN (FIXED in this session - needs redeploy)

---

### GUI-ACT-DS-CREATE (DatasetModal)

**User Intent:** Create dataset from selected images

**Expected Chain:**
1. UI Event: Button click `@click="createDataset"`
2. Validation: `canCreateDataset` computed
3. Network request: `POST /api/datasets/datasets`
4. Backend endpoint: `datasets.py:@router.post("/datasets")`
5. Response: Dataset object
6. Post-response: emit 'created', close modal

**Verification:**
- [x] Handler bound: `@click="createDataset"` (line 201)
- [x] Function exists: `createDataset()` (line 307-334)
- [x] API call: `datasetApi.createDataset(datasetConfig)` (line 324)
- [x] Backend route: `@router.post("/datasets")` in `datasets.py`
- [!] **BUG IN UPLOAD:** Line 297 calls `mediaApi.uploadFile(file)` but method is `mediaApi.upload()`

**Breakpoint:** `DatasetModal.vue:297` calls non-existent `mediaApi.uploadFile()`

**Status:** ❌ BROKEN (FIXED in this session - needs redeploy)

---

## Create Character Screen

### GUI-ACT-CREATECHAR-SUBMIT

**User Intent:** Create a new character

**Expected Chain:**
1. UI Event: Form submit / Button click
2. Validation: `canCreate` computed must be true
3. Pre-upload: If image is File, upload first
4. Network request: `POST /api/training/characters`
5. Backend endpoint: `training.py:@router.post("/characters")`
6. Response: Character object with id
7. Post-response: Navigate to `/characters/{id}`

**Verification:**
- [x] Button exists with `:disabled="!canCreate || isCreating"`
- [x] Handler: `@click="createCharacter"`
- [x] Function: `createCharacter()` (line 686-737)
- [x] API call: `charactersApi.create({name, input_image_path})` (line 723)
- [x] Backend route: `@router.post("/characters")` in `training.py:101`

**Validation Check (`canCreate` computed):**
```javascript
const canCreate = computed(() => {
  const hasName = form.value.name.trim().length > 0
  const hasTriggerWord = form.value.triggerWord.trim().length > 0
  const hasImageOrDataset = selectedImage.value || form.value.datasetId
  const validParams = validateTrainingParameters()
  return hasName && hasTriggerWord && hasImageOrDataset && validParams
})
```

**Potential Issues:**
1. `validateTrainingParameters()` checks many numeric fields - string/number coercion issues possible
2. Backend validates `Path(input_image_path).exists()` - path must exist on server filesystem
3. `triggerWord` is required by frontend but NOT by backend `CharacterCreateRequest`

**Breakpoint:** Multiple validation gates. Debug logging added to identify which fails.

**Status:** ⚠️ NEEDS INVESTIGATION (debug logging added)

---

### GUI-ACT-CREATECHAR-IMGSELECT

**User Intent:** Select image from media library

**Expected Chain:**
1. UI Event: Button click `@click="openMediaLibrary"`
2. Check: `mediaFiles.value.length > 0`
3. State: `showMediaLibrary = true`
4. Modal: Display media files grid
5. Selection: Click image → `selectImageFromLibrary(file)`
6. State: `selectedImage = file`, modal closes

**Verification:**
- [x] Handler: `@click="openMediaLibrary"` (line ~103)
- [x] Function: `openMediaLibrary()` (line 597-604)
- [x] Check for empty library with toast warning
- [x] Selection handler: `selectImageFromLibrary(file)` (line 679-684)
- [x] Debug logging added

**Potential Issue:** If `loadMediaFiles()` fails silently, library appears empty

**Status:** ✅ WORKING (with debug logging)

---

## Characters Screen

### GUI-ACT-CHAR-START-TRAIN

**User Intent:** Start training for a created character

**Expected Chain:**
1. UI Event: Button click `@click.stop="startTraining(character)"`
2. Network request: `POST /api/training/characters/{id}/train`
3. Backend endpoint: `training.py:@router.post("/characters/{character_id}/train")`
4. Response: TrainingSession object
5. Post-response: Navigate to training view

**Verification:**
- [x] Handler: `@click.stop="startTraining(character)"` (line 86)
- [x] Function: `startTraining()` (line 226-243)
- [x] API call: `trainingApi.startTraining(character.id, config)` (line 228)
- [x] Backend route: `@router.post("/characters/{character_id}/train")` in `training.py`

**Status:** ✅ WORKING

---

### GUI-ACT-CHAR-DELETE

**User Intent:** Delete a character

**Expected Chain:**
1. UI Event: Button click `@click="deleteCharacter(selectedCharacter)"`
2. Confirm dialog
3. Network request: DELETE endpoint (NOT IMPLEMENTED)
4. Post-response: Remove from list

**Verification:**
- [x] Handler: `@click="deleteCharacter(selectedCharacter)"` (line 171)
- [x] Function: `deleteCharacter()` (line 260-275)
- [!] **BUG:** Line 267 comments out API call: `// await charactersApi.delete(character.id)`
- [!] **MISSING:** `charactersApi.delete()` not defined in api.ts
- [!] **MISSING:** Backend DELETE endpoint not implemented

**Breakpoint:** Delete is frontend-only (removes from array but not from database)

**Status:** ❌ NOT IMPLEMENTED

---

## Inference Screen

### GUI-ACT-INF-GENERATE

**User Intent:** Generate images using trained LoRA

**Expected Chain:**
1. UI Event: Form submit `@submit.prevent="generateImages"`
2. Validation: `canGenerate` (character_id + prompt required)
3. Network request: `POST /api/inference/generate`
4. Backend endpoint: `inference.py:@router.post("/generate")`
5. Response: InferenceJob with id
6. Post-response: Show results modal, poll for completion

**Verification:**
- [x] Handler: `@submit.prevent="generateImages"` (line 14)
- [x] Function: `generateImages()` (line 404-435)
- [x] API call: `inferenceApi.generate(config)` (line 409)
- [x] Backend route: `@router.post("/generate")` in `inference.py:59`
- [x] Polling: `pollJobStatus()` (line 437-460)

**Status:** ✅ WORKING

---

## Identified Issues Summary

### Critical Issues (Blocks Core Functionality)

| # | Issue | File | Line | Impact |
|---|-------|------|------|--------|
| 1 | `files` undefined, should be `mediaFiles` | MediaView.vue | 204 | Dataset modal crashes page |
| 2 | `mediaApi.uploadFile()` doesn't exist | DatasetModal.vue | 297 | Upload in modal fails |
| 3 | HTTP method mismatch (GET vs POST) | api.ts / settings.py | 219 / varies | Test Environment fails |
| 4 | Character delete not implemented | CharactersView.vue | 267 | Delete is fake |
| 5 | Backend path validation may fail | training.py | 125 | Character creation fails |

### Medium Issues (Degraded Experience)

| # | Issue | File | Line | Impact |
|---|-------|------|------|--------|
| 6 | CharacterDetailView is placeholder | CharacterDetailView.vue | all | No character details |
| 7 | TrainingView doesn't load sessions | TrainingView.vue | 285 | Always empty |
| 8 | triggerWord required on frontend, not backend | CreateCharacterView.vue | varies | Confusing UX |

### Already Fixed (This Session)

| # | Issue | Status |
|---|-------|--------|
| A | DatasetModal files prop (Issue #1) | ✅ Fixed, synced to pod |
| B | mediaApi.uploadFile typo (Issue #2) | ✅ Fixed, synced to pod |

---

## Proposed Fixes

### Fix #3: Settings Test Environment HTTP Method

**File:** `charforge-gui/frontend/src/services/api.ts`
**Change:** Line 219-220
```typescript
// FROM:
testEnvironment: (): Promise<Record<string, { valid: boolean; message: string }>> =>
  api.get('/settings/test-environment').then(res => res.data),

// TO:
testEnvironment: (): Promise<Record<string, { valid: boolean; message: string }>> =>
  api.post('/settings/test-environment').then(res => res.data),
```
**Verification:** Click "Test Configuration" button, should show results.

---

### Fix #4: Implement Character Delete

**File 1:** `charforge-gui/frontend/src/services/api.ts`
**Add:**
```typescript
delete: (id: number): Promise<{ message: string }> =>
  api.delete(`/training/characters/${id}`).then(res => res.data),
```

**File 2:** `charforge-gui/backend/app/api/training.py`
**Add after line 165:**
```python
@router.delete("/characters/{character_id}")
async def delete_character(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Delete a character."""
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()

    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    db.delete(character)
    db.commit()
    return {"message": "Character deleted"}
```

**File 3:** `charforge-gui/frontend/src/views/CharactersView.vue`
**Change line 267:**
```typescript
// FROM:
// await charactersApi.delete(character.id)

// TO:
await charactersApi.delete(character.id)
```

---

### Fix #5: Robust Image Path Handling

**File:** `charforge-gui/backend/app/api/training.py`
**Change lines 124-129:**
```python
# FROM:
if not request.input_image_path or not Path(request.input_image_path).exists():
    raise HTTPException(...)

# TO:
image_path = Path(request.input_image_path)
# Also check relative to media directory
if not image_path.exists():
    media_path = settings.MEDIA_DIR / request.input_image_path.lstrip('/')
    if not media_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image not found: {request.input_image_path}"
        )
```

---

## Top 5 Systemic Issues & Recommended Fix Order

1. **HTTP Method Consistency** - Frontend/backend method mismatches (GET vs POST)
   - Quick fix, high impact on Settings page

2. **Missing CRUD Operations** - Delete endpoints not implemented
   - Medium effort, needed for complete UX

3. **Undefined Variable References** - Props/vars referenced before definition
   - Already fixed two cases, audit for more

4. **Path Resolution** - Backend expects absolute paths, frontend sends relative
   - Critical for character creation flow

5. **Placeholder Views** - CharacterDetailView, parts of TrainingView incomplete
   - Lower priority, degrades experience but doesn't block

**Recommended Fix Order:**
1. Fix #3 (HTTP method) - 2 min
2. Fix #5 (path handling) - 5 min
3. Fix #4 (delete endpoint) - 10 min
4. Audit all views for similar undefined variable issues
5. Implement placeholder views

---

## Verification Commands

```bash
# Check for undefined variable references in Vue files
grep -r ":files=" charforge-gui/frontend/src --include="*.vue" | grep -v "mediaFiles\|files\."

# Check for HTTP method consistency
grep -E "api\.(get|post|put|delete)" charforge-gui/frontend/src/services/api.ts

# Check backend route methods
grep -E "@router\.(get|post|put|delete)" charforge-gui/backend/app/api/*.py
```
