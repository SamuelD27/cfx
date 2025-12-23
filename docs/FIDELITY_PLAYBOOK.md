# Fidelity Playbook: Maximizing Identity Accuracy

[Back to README](../README.md)

This document provides deep guidance for maximizing identity fidelity - the degree to which generated images are indistinguishable from photos of the reference person.

---

## Reference Image Selection Checklist

The reference image is the foundation. Every flaw propagates.

### Mandatory Requirements

- [ ] **Resolution**: 512x512 minimum, 1024x1024+ optimal
- [ ] **Face Size**: Face occupies at least 30% of image area
- [ ] **Focus**: Face is in sharp focus (not motion-blurred)
- [ ] **Occlusions**: No sunglasses, hats, masks, hands on face
- [ ] **Other Faces**: No other people visible in frame

### Optimal Conditions

- [ ] **Lighting**: Even, diffused (overcast outdoor, studio softbox)
- [ ] **Angle**: Frontal or slight 3/4 view (15-30 degrees max)
- [ ] **Expression**: Neutral, mouth closed, or slight natural smile
- [ ] **Background**: Solid color or heavily blurred
- [ ] **Color**: No extreme color casts (avoid blue/orange party lighting)

### Red Flags (Avoid)

| Issue | Why It Hurts Fidelity |
|-------|----------------------|
| Harsh shadows | Multi-view generation struggles; lighting artifacts baked in |
| Extreme expressions | Emotion variations will be unnatural |
| Profile views | Pipeline assumes frontal; back-of-head generation fails |
| Low resolution | Upscaling introduces artifacts; face details lost |
| Heavy makeup/filters | LoRA learns the filter, not the face |
| Busy backgrounds | MV-Adapter may incorporate background elements |

### Testing Your Reference

Before training, visually verify:

1. Can you clearly see both eyes?
2. Is the nose shape clearly defined?
3. Are both ears visible (or at least one)?
4. Is the jawline distinct from the background?
5. Are there any shadows crossing the face?

If any answer is "no" or "barely", find a better reference.

---

## Understanding the Training Data

The pipeline generates 13+ images from your single reference:

### Multi-View Images (High Fidelity Contribution)

| Image | View | What It Teaches |
|-------|------|-----------------|
| `upscaled_multiview_0.png` | Front | Baseline face structure |
| `upscaled_multiview_1.png` | 45° left | Left profile features |
| `upscaled_multiview_2.png` | 90° left | Full left profile |
| `upscaled_multiview_3.png` | Back | Hair/head shape |
| `upscaled_multiview_4.png` | 90° right | Full right profile |
| `upscaled_multiview_5.png` | 45° right | Right profile features |

**Fidelity Impact**: These are critical. They teach the model that this face has consistent 3D structure. Errors here cause inconsistent face shapes across angles.

### Lighting Variations (Medium Fidelity Contribution)

| Image | Condition | Purpose |
|-------|-----------|---------|
| `upscaled_lighting_0.png` | Overcast | Diffused natural light |
| `upscaled_lighting_1.png` | Sunset | Warm directional light |
| `upscaled_lighting_2.png` | Nightclub | Colored artificial light |
| `upscaled_lighting_3.png` | Desert | Bright natural light |

**Fidelity Impact**: Prevents the LoRA from overfitting to the original image's lighting. Without these, generated images may only look correct in similar lighting.

### Emotion Variations (Medium Fidelity Contribution)

| Image | Expression | Purpose |
|-------|------------|---------|
| `upscaled_emotions_1.png` | Eyes closed | Teaches eyelid shape |
| `upscaled_emotions_3.png` | Laughing | Teaches mouth/teeth |

**Fidelity Impact**: Without expression variety, the model may struggle with non-neutral expressions or produce uncanny results.

### PuLID-Flux Images (Variable Contribution)

If `--pulidflux_images N` is used, N synthetic images are generated.

**When They Help**:
- Diverse backgrounds and contexts
- Additional pose variety
- More data for complex identities

**When They Hurt**:
- If N is too high (>5), synthetic artifacts average into the LoRA
- If the PuLID generation drifts, it teaches wrong features
- Dilutes the influence of real data

**Recommendation**: Start with 0. If identity is weak, add 3-5. Never exceed 10.

---

## Captioning Implications

Each image has a `.txt` caption file. Captions affect what the LoRA associates with the face.

### Caption Format

The pipeline uses `image_info.json` to provide partial captions that the captioner expands:

```
"upscaled_multiview_1.png": {
    "description": "photorealistic, Three-quarters view from the left side..."
}
```

### Fidelity Rules for Captions

1. **Never include names**: The LoRA should not associate text with identity
2. **Avoid unique identifiers**: No "celebrity", "famous", specific locations
3. **Keep descriptions visual**: Focus on pose, lighting, expression
4. **Maintain consistency**: All captions should use similar vocabulary

### Checking Captions

```bash
# View all captions
cat ./scratch/NAME/sheet/*.txt

# Look for problematic content
grep -i "name\|famous\|celebrity" ./scratch/NAME/sheet/*.txt
# Should return nothing
```

### Fixing Captions

If captions are polluted, you can edit them manually then retrain:

```bash
# Edit caption
nano ./scratch/NAME/sheet/upscaled_multiview_0.txt

# Retrain LoRA only (skip sheet generation)
# Note: Currently no CLI flag; must regenerate full pipeline
```

---

## Inference Prompt Patterns

### Identity Lock Tokens

This pipeline does not use explicit trigger words (like `sks` or `ohwx`). The LoRA encodes identity directly.

**Key insight**: The identity is in the LoRA weights, not in special tokens. Your prompt describes the scene; the LoRA adds the face.

### Prompt Structure for Maximum Fidelity

```
[Quality tokens], [Subject descriptor], [Scene/Action], [Lighting], [Technical details]
```

#### Quality Tokens (Start of Prompt)

Good:
- `photorealistic, highly detailed, 8k`
- `professional photograph, sharp focus`
- `natural lighting, authentic`

Avoid:
- `anime, cartoon, stylized`
- `oil painting, watercolor`
- `abstract, surreal`

#### Subject Descriptor

Good:
- `a person` (neutral)
- `a young professional` (contextual)
- `portrait of someone` (generic)

Avoid:
- Specific names (never)
- Celebrity comparisons (causes drift)
- Contradictory descriptions (`old man` for young person)

#### Scene/Action

Good:
- `sitting in a modern office`
- `walking through a park`
- `speaking at a conference`

Avoid:
- Extreme poses the model never saw
- Situations contradicting the identity (wrong age/context)
- Heavily stylized environments

### Example Prompts (High Fidelity)

```bash
# Professional headshot
--prompt "photorealistic portrait, professional headshot, studio lighting, neutral gray background, sharp focus, 8k"

# Casual outdoor
--prompt "natural photograph of a person outdoors, golden hour lighting, candid pose, shallow depth of field"

# Business context
--prompt "professional photo, person in business attire, modern office environment, natural window light"
```

### Example Prompts (Lower Fidelity - Use with Caution)

```bash
# Heavy styling (may drift)
--prompt "dramatic cinematic portrait, film noir lighting, high contrast"

# Unusual context (untested poses)
--prompt "person doing a backflip in a gym"

# Conflicting style (fights LoRA)
--prompt "anime style portrait" # WILL fail
```

---

## Diagnosing Identity Drift

### Symptoms

| Symptom | Likely Cause |
|---------|--------------|
| Face shape changes between images | Low LoRA weight or prompt conflicts |
| Skin tone inconsistent | Lighting terms in prompt overriding |
| Eye color shifts | Base model defaulting; increase LoRA weight |
| Different person entirely | LoRA not loading or wrong path |
| Right face but uncanny | FaceEnhance artifacts or bad training data |

### Diagnostic Steps

1. **Check LoRA is loading**:
   ```bash
   # Should print "LoRA loaded from: ..."
   python test_character.py ... 2>&1 | grep "LoRA loaded"
   ```

2. **Test at high LoRA weight**:
   ```bash
   python test_character.py ... --lora_weight 0.95
   # If identity is strong, your default weight is too low
   ```

3. **Test with minimal prompt**:
   ```bash
   python test_character.py --character_name NAME --prompt "portrait"
   # If this works but complex prompts don't, prompt is conflicting
   ```

4. **Review training data**:
   ```bash
   open ./scratch/NAME/sheet/
   # Visually inspect all images
   # Look for artifacts, wrong faces, or corrupted images
   ```

### Fixes

| Diagnosis | Fix |
|-----------|-----|
| LoRA weight too low | Increase `--lora_weight` to 0.8-0.9 |
| Prompt conflicts | Simplify prompt; remove style tokens |
| Bad training images | Re-run with better reference |
| Too many PuLID images | Re-train with `--pulidflux_images 0` |
| Captions polluted | Edit `.txt` files, retrain |

---

## Fidelity Validation Tests

### Test 1: Repeatability

Generate 4 images with identical prompt:
```bash
python test_character.py --character_name NAME \
  --prompt "professional headshot, studio lighting" \
  --batch_size 4
```

**Pass**: All 4 faces are clearly the same person
**Fail**: Faces vary significantly between images

### Test 2: Pose Variance

Generate with different poses:
```bash
# Frontal
python test_character.py ... --prompt "portrait, looking directly at camera"

# 3/4 view
python test_character.py ... --prompt "portrait, slight angle, looking away"

# Profile
python test_character.py ... --prompt "profile view portrait"
```

**Pass**: Face maintains identity across all angles
**Fail**: Side views look like different person

### Test 3: Expression Variance

```bash
python test_character.py ... --prompt "laughing portrait"
python test_character.py ... --prompt "serious expression portrait"
python test_character.py ... --prompt "surprised expression portrait"
```

**Pass**: Expressions change but identity maintained
**Fail**: Different expressions produce different identities

### Test 4: Prompt Robustness

```bash
# Simple
python test_character.py ... --prompt "portrait"

# Complex
python test_character.py ... --prompt "cinematic portrait in a rainy city at night, neon reflections"
```

**Pass**: Identity maintained even with complex prompts
**Fail**: Complex prompts override identity

---

## Advanced Fidelity Tuning

### Training Parameters for Higher Fidelity

```bash
python train_character.py \
  --name "NAME" \
  --input "ref.jpg" \
  --steps 1200 \        # More training (default 800)
  --rank_dim 16 \       # Higher capacity (default 8)
  --train_dim 768       # Higher resolution (default 512)
```

**Trade-offs**:
- More steps: Better identity, but risk overfitting
- Higher rank: More capacity, but larger LoRA file
- Higher resolution: More detail, but longer training

### When to Use PuLID-Flux

Add synthetic images only if:
1. Base training (0 PuLID) produces weak identity
2. You need more pose/context variety
3. You've verified PuLID outputs match the identity

```bash
# Cautious approach
python train_character.py ... --pulidflux_images 3
```

---

[Back to README](../README.md) | [Operator Guide](OPERATOR_GUIDE.md) | [Troubleshooting](TROUBLESHOOTING.md)
