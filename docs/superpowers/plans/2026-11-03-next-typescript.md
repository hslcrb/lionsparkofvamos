# Next.js TypeScript Migration Implementation Plan

Goal: Convert all application, Worker and test code to strict TypeScript and Next.js App Router, preserving the current routes, design and live data.

Architecture: Next.js statically renders each public route; the existing Cloudflare Worker serves those exports and owns the WebSocket Durable Object. App Router handles navigation. A persistent client music provider owns playback; focused hooks own room connections and interaction state. Three.js scene construction is separated from React controls.

Constraints: Only the Lions Park project. Preserve CheerRoom name, cinema instance, SQLite schema and migration v1. Preserve /main, /lionspark, HTTP 404/418 and gain 0.1 with 3-second fade. Keep original supplied audio untouched.

- [x] Install Next.js, TypeScript and type/lint tools; replace Vite entry/config/scripts.
- [x] Add strict protocol validation tests, migrate typed shared protocol, gestures and audio.
- [x] Replace manual history routing with App Router pages, metadata, not-found/error boundaries and music provider.
- [x] Split room lifecycle, cheer interactions and 3D renderer into typed modules; preserve presentation.
- [x] Migrate Worker and tests; serve distinct exported route HTML and retain status codes, assets and WebSocket origin checks.
- [x] Remove unused entry styles, document commands and add CI quality checks.
- [x] Run focused tests, type checks, lint, one complete test suite and production build; inspect local browser flow and HTTP/WebSocket behavior.
Release procedure: merge the verified branch to main, push, and verify the exact revision in Cloudflare Builds and the live pages.

Review focus: malformed room messages; reconnect and unmount cleanup; blocked or rapidly toggled music; direct and client navigation; 3D resource disposal and reduced motion.
