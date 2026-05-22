// Lofi Girl — Approach B rich atmospheric shader
// Pairs with background-image = lofi-girl.png (static frame)
// Animates: rain streaks, amber lamp bloom, film grain, vignette
// The shader IS the animation — no GIF needed.

#define GRAIN_STRENGTH  0.055
#define WARMTH          0.07
#define VIGNETTE        0.40
#define RAIN_LAYERS     4.0
#define RAIN_SPEED      0.55
#define RAIN_OPACITY    0.045   // very subtle — room is cozy, not stormy
#define LAMP_FLICKER    0.018   // subtle flicker amplitude

// ── Utilities ────────────────────────────────────────────────────────────────

float hash1(float n) { return fract(sin(n) * 43758.5453123); }
float hash2(vec2 p)  { p = fract(p * vec2(234.56, 789.01)); p += dot(p, p + 45.32); return fract(p.x * p.y); }

// ── Film grain ────────────────────────────────────────────────────────────────

float grain(vec2 uv) {
    return hash2(uv + fract(iTime * 0.07)) * 2.0 - 1.0;
}

// ── Rain streaks ──────────────────────────────────────────────────────────────
// Thin vertical streaks, slight diagonal, only visible in darker regions.

float rainLayer(vec2 uv, float layer) {
    float speed  = RAIN_SPEED * (0.7 + layer * 0.15);
    float slant  = 0.12 * layer;                          // slight diagonal
    float cols   = 40.0 + layer * 8.0;
    float rows   = 25.0 + layer * 4.0;

    // Offset UVs per layer for variety
    vec2 off = vec2(layer * 0.31, layer * 0.17);
    vec2 ruv = uv + off;
    ruv.x += ruv.y * slant;

    // Cell coordinates
    vec2 cell = floor(ruv * vec2(cols, rows));
    vec2 frac = fract(ruv * vec2(cols, rows));

    // Random drop per cell column: active if hash < density
    float density = 0.25 - layer * 0.04;
    float active  = step(1.0 - density, hash1(cell.x + layer * 137.1));

    // Vertical animation: drop falls down
    float dropY = fract(hash1(cell.x + layer * 73.3) - iTime * speed);
    float streak = smoothstep(0.0, 0.12, dropY) * (1.0 - smoothstep(0.12, 0.30, dropY));

    // Thin streak in x-axis
    float thin = smoothstep(0.45, 0.50, frac.x) * (1.0 - smoothstep(0.50, 0.55, frac.x));

    return active * streak * thin * (0.6 + 0.4 * hash1(cell.x * cell.y + layer));
}

// ── Lamp bloom ───────────────────────────────────────────────────────────────
// Warm amber cone emanating from upper-right (where the desk lamp sits).

vec3 lampBloom(vec2 uv) {
    // Lamp origin: upper-right quadrant, roughly where lamp is in scene
    vec2 origin = vec2(0.72, 0.10);

    // Directional cone pointing down-left toward the desk
    vec2 dir    = uv - origin;
    float dist  = length(dir);

    // Cone angle: lamp points roughly toward lower-left
    vec2  lampDir  = normalize(vec2(-0.55, 0.85));
    float cone     = dot(normalize(dir), lampDir);
    float coneMask = smoothstep(0.55, 0.85, cone);   // tight cone

    // Falloff with distance
    float falloff = 1.0 / (1.0 + dist * dist * 18.0);

    // Flicker: gentle sin oscillation
    float flicker  = 1.0 + LAMP_FLICKER * sin(iTime * 3.7 + 1.2)
                         + LAMP_FLICKER * 0.5 * sin(iTime * 8.1);

    float intensity = coneMask * falloff * flicker * 0.22;

    // Warm amber color
    return vec3(0.95, 0.58, 0.22) * intensity;
}

// ── Main ──────────────────────────────────────────────────────────────────────

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv  = fragCoord.xy / iResolution.xy;
    vec4 term = texture(iChannel0, uv);
    vec3 col  = term.rgb;

    // Warm color tint
    col.r = clamp(col.r + WARMTH * 0.8, 0.0, 1.0);
    col.g = clamp(col.g + WARMTH * 0.3, 0.0, 1.0);

    // Rain — only show in darker pixels (window/background, not bright text)
    float lum  = dot(col, vec3(0.2126, 0.7152, 0.0722));
    float mask = 1.0 - smoothstep(0.25, 0.55, lum);  // fade rain out of bright areas
    float rain = 0.0;
    for (float i = 0.0; i < RAIN_LAYERS; i++) {
        rain += rainLayer(uv, i);
    }
    col += vec3(0.72, 0.82, 0.92) * rain * RAIN_OPACITY * mask;

    // Lamp bloom — additive, sits on top
    col += lampBloom(uv);

    // Film grain
    col += grain(uv) * GRAIN_STRENGTH;

    // Vignette
    vec2  c    = abs(uv * 2.0 - 1.0);
    vec2  edge = clamp((c - 0.58) / 0.42, 0.0, 1.0);
    float vig  = 1.0 - edge.x * edge.y * VIGNETTE;
    col *= vig;

    fragColor = vec4(clamp(col, 0.0, 1.0), term.a);
}
