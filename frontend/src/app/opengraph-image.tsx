import { ImageResponse } from "next/og";

export const alt = "ContestForge — Live Contest Platform";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "linear-gradient(135deg, #4f46e5 0%, #312e81 100%)",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          color: "white",
          padding: 64,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 24,
            marginBottom: 32,
          }}
        >
          <div
            style={{
              width: 72,
              height: 72,
              borderRadius: 16,
              background: "rgba(255,255,255,0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 40,
            }}
          >
            🏆
          </div>
          <div
            style={{
              fontSize: 72,
              fontWeight: 800,
              letterSpacing: "-0.025em",
            }}
          >
            ContestForge
          </div>
        </div>
        <div
          style={{
            fontSize: 36,
            fontWeight: 500,
            opacity: 0.9,
            textAlign: "center",
            maxWidth: 900,
          }}
        >
          Run timed competitive quizzes at scale. Multi-tenant live contest
          engine for 10,000+ concurrent participants.
        </div>
      </div>
    ),
    {
      ...size,
    }
  );
}
