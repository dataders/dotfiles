// Corner-focused vignette — darkens corners only, leaves side edges clear.
// Strength tunable via STRENGTH: 0.0 = off, 0.25 = gentle, 0.5 = noticeable.
#define STRENGTH 0.30

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord.xy / iResolution.xy;
    vec4 color = texture(iChannel0, uv);

    // Signed distance from center in [-1, 1] on each axis
    vec2 centered = uv * 2.0 - 1.0;

    // Corner-only: each axis ramps from 0→1 in the outer 35% of its range,
    // multiplied so both axes must be large — pure side edges get dist=0.
    vec2 c = abs(centered);
    vec2 edge = clamp((c - 0.65) / 0.35, 0.0, 1.0);
    float dist = edge.x * edge.y;   // 0..1, peaks only at corners
    float vignette = 1.0 - dist * STRENGTH;

    fragColor = vec4(color.rgb * vignette, color.a);
}
