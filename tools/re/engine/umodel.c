/* engine.dll — UModel reconstruction (progressive; x86 MSVC, RVA base 0x10300000).
 * Source of truth: the disassembly from craft-anything (2026-11-17) +
 * Docs/EngineRE.md. Each function cites its entry RVA. Continue filling in
 * as disassembly progresses; goal = 100% source of the reversed parts.
 *
 * Addresses: engine.dll image base is assumed 0x10300000 in the listings
 * (the tool reports the linked addresses); keep the cited RVAs verbatim.
 */

#include <stdint.h>

typedef struct { float x, y, z; } FVector;
typedef struct { float x, y, z, w; } FPlane;

/* ---- Forward structures (offsets are the in-memory layout measured in the
 *      disassembly; expand as more fields are identified) ----------------- */

/* UModel (relevant fields) */
typedef struct UModel UModel;
struct UModel {
    uint8_t  pad0[0x64];        /* 0x00..0x63 unknown here */
    void    *SurfRenderData;    /* 0x64: TArray data of 120-B surf records */
    int32_t  SurfRenderCount;   /* 0x68: its count */
    uint8_t  pad1[0x38];        /* 0x6C..0xA3 */
    FVector *Points;            /* 0xA4: the model Points array (base) */
    uint8_t  pad2[0x40];        /* 0xA8..0xE7 */
    void    *SectionsData;      /* 0xE4: TArray<FBspSection> data */
    int32_t  SectionsCount;     /* 0xE8: its count */
    uint8_t  pad3[0x20];        /* 0xEC..0x10B */
    void    *LightMapData;      /* 0x10C: light-map entries, 0xAC B each */
    uint8_t  pad4[0x08];
};

/* FBspSection — 0x34 = 52 bytes; ctor @0x10311077 */
typedef struct FBspSection FBspSection;
struct FBspSection {
    uint8_t  pad0[0x18];        /* 0x00..0x17 */
    int32_t  VertCount0;        /* 0x18: first-vertex counter (+= NumVertices) */
    int32_t  VertCount1;        /* 0x1C: second counter (+= NumVertices) */
    uint8_t  pad1[0x04];
    void    *Material;          /* 0x20: grouping key 1 (UMaterial*) */
    uint32_t FlagsMasked;       /* 0x24: grouping key 2 = PolyFlags & 0x2400100 */
    int32_t  LightMap;          /* 0x28: grouping key 3 */
    uint8_t  pad2[0x0C];        /* 0x2C..0x33 */
};

/* In-memory surf render record (120 B, stride of the 0x64/0x68 array) —
 * the fields BuildRenderData/PostLoad touch; names per UE2 FBspSurf. */
typedef struct {
    uint8_t  pad0[0x18];        /* 0x00..0x17 */
    int32_t  iVertPool;         /* 0x18: first vertex index */
    uint8_t  pad1[0x3E];        /* 0x1C..0x55 */
    uint8_t  NumVertices;       /* 0x56 */
    uint8_t  pad2[0x09];        /* 0x57..0x5F */
    int32_t  iSection;          /* 0x60: written back by BuildRenderData */
    void    *SectionVertArray;  /* 0x64: the appended vertex list */
    uint8_t  pad3[0x08];        /* 0x68..0x6F */
    int32_t  LightMapIndex;     /* 0x68 hmm — overlaps pad3; see note */
    uint8_t  pad4[0x08];        /* ... to 0x77 = 120 B */
} SurfRec;
/* NOTE: the disassembly reads [esi+0x68] as an INT light-map index and
 * [esi+0x56] as the byte vertex count, [esi+0x18] as the vertex start.
 * The 120-B record is NOT the file FBspSurf; refine as more is decoded. */

/* ---- The PolyFlags the engine cares about (UE2 UnObj.h:236) ------------ */
enum {
    PF_Invisible   = 0x00000001,
    PF_NotSolid    = 0x00000008,
    PF_TwoSided    = 0x00000100,
    PF_Unused2     = 0x00002000,   /* L2 repurposed */
    PF_Unused3     = 0x00008000,   /* L2 repurposed */
    PF_Unlit       = 0x00400000,
    PF_Portal      = 0x04000000,
    PF_Mirrored    = 0x20000000,
};
#define SECTION_KEY_MASK 0x2400100   /* TwoSided | Portal | Mirrored */

/* ---- UModel::PostLoad @0x10312cba (46 instructions, fully decoded) -----
 * jmp 0x105eab20:
 *   for (i = 0; i < SurfRenderCount; ++i) {
 *       SurfRec *s = &SurfRenderData[i];
 *       sub_1031502d(&Points[s->iVertPool ... surf pBase +0x20], &i);
 *   }
 *   UObject::PostLoad();
 * NO poly->surf building: the runtime does NOT run CSG. The surfs arrive
 * baked in the .unr (the editor shipped the CSG result). */
void UModel_PostLoad(UModel *this_)            /* @0x10312cba */
{
    for (int32_t i = 0; i < this_->SurfRenderCount; ++i) {
        SurfRec *s = (SurfRec *)((uint8_t *)this_->SurfRenderData + i * 120);
        /* sub_1031502d(&Points[... +0x20], &i); — fixup of the surf's
         * pBase point record; body not yet decoded. */
        sub_1031502d((uint8_t *)this_->Points + /* ... */ 0 + 0x20, &i);
    }
    UObject_PostLoad(this_);
}

/* ---- UModel::BuildRenderData @0x10307c98 (404 instructions) ------------
 * jmp 0x105ee860. The run (from the disassembly):
 *
 *   ClearRenderData(NULL);
 *   for (si = 0; si < SurfRenderCount; ++si) {
 *       SurfRec *s = &SurfRenderData[si];
 *       if (s->LightMapIndex != -1)
 *           lm = (FLightMapEntry *)((uint8_t*)LightMapData + s->LightMapIndex * 0xAC);
 *       else lm = NULL;
 *       mat = s->Material ? s->Material
 *                         : default_material->field_0x38 (via GetDefaultObject);
 *       key_flags = PolyFlags & SECTION_KEY_MASK;          // 0x2400100
 *       lm_idx = lm ? lm->field_0x10 : -1;
 *       if (s->NumVertices == 0) continue;
 *
 *       // find/create the FBspSection with keys (mat, key_flags, lm_idx):
 *       for (k = 0; k < SectionsCount; ++k) {
 *           FBspSection *sec = &SectionsData[k];
 *           if (sec->Material == mat && sec->FlagsMasked == key_flags &&
 *               sec->LightMap == lm_idx &&
 *               sec->VertCount0 + s->NumVertices <= 0xFFFF) {
 *               use = sec; break;
 *           }
 *       }
 *       if (!use) { use = SectionArray_Add(&SectionsData, 0x34); ctor(use); }
 *       use->Material = mat; use->FlagsMasked = key_flags; use->LightMap = lm_idx;
 *       s->iSection = (use - SectionsData);                 // 0x4EC4EC4F magic
 *                                                                   // = /52
 *       use->verts = FArray_Add(&use->verts, s->NumVertices, 0x28); // 40 B/vert
 *
 *       FCoords c(Points[s->iVertPool], Points[surf+0x14], Points[surf+0x10],
 *                 Points[surf+0x0C]);                       // base/U/V vectors
 *       FMatrix m = c.Matrix();
 *       texscale = s->Material->GetTextureSize? (vtable+0x80 / +0x84 -> INT)
 *       for (v = 0; v < s->NumVertices; ++v) {
 *           p = Points[Verts[s->iVertPool + v].index];       // model+0x94 pool
 *           out.pos = p transformed by c;
 *           out.u = dot(p, U) / texscale_u;
 *           out.v = dot(p, V) / texscale_v;                  // + per-face shift
 *           ... centers the UVs (mean subtracted, appRound)
 *           out.normal = s->normal; out.lightmap = lm fields (+0x1C/+0x20/+0x24)
 *       }
 *       use->VertCount0 += s->NumVertices; use->VertCount1 += s->NumVertices;
 *   }
 *
 * KEY FACT: the mask 0x2400100 groups the sections; it does NOT filter.
 * All other PolyFlags are stripped — they cannot gate rendering here. */
