# Grocery List Frontend

A modern, mobile-first Next.js frontend for the Grocery List Structuring Engine.

## Features

- **Home Screen**: Dashboard showing active and recent grocery lists
- **List View**: View and manage items grouped by category with checkbox support
- **Quick Add**: Bottom sheet for quickly adding multiple items via text input
- **AI-Powered Parsing**: Integrates with the FastAPI backend to parse and structure grocery items

## Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Smooth animations
- **Material Symbols** - Google's icon system

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Environment Variables

Create a `.env.local` file:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx            # Home screen
│   │   ├── layout.tsx          # Root layout
│   │   ├── globals.css         # Global styles
│   │   └── list/
│   │       ├── [id]/page.tsx   # List detail view
│   │       └── new/page.tsx    # Create new list
│   ├── components/             # Reusable components
│   │   ├── Icon.tsx            # Material Symbols wrapper
│   │   ├── StatusBar.tsx       # Mobile status bar
│   │   ├── ListCard.tsx        # List card component
│   │   ├── GroceryItem.tsx     # Individual item row
│   │   ├── CategorySection.tsx # Category grouping
│   │   ├── QuickAddSheet.tsx   # Bottom sheet for adding items
│   │   └── BottomToolbar.tsx   # Floating bottom toolbar
│   ├── lib/
│   │   └── api.ts              # API client functions
│   └── types/
│       └── index.ts            # TypeScript type definitions
├── tailwind.config.ts          # Tailwind configuration
├── next.config.js              # Next.js configuration
└── package.json
```

## Screens

### Home Screen (`/`)
- Shows active list with progress
- Recent lists section
- "Create New List" button

### List View (`/list/[id]`)
- Items grouped by category
- Checkbox to mark items complete
- Floating toolbar with quick add button

### New List (`/list/new`)
- Quick add sheet opens automatically
- Type or paste items to add
- Real-time preview of parsed items

## Integration with Backend

The frontend calls the FastAPI backend at `POST /api/v1/parse-list` to:
1. Parse raw text input into structured items
2. Receive normalized product names, quantities, units
3. Display resolved items in the UI

## Design System

### Colors
- Primary: `#10B981` (emerald green)
- Background: Light gray (`#f8faf8`) / Dark (`#0f1a0f`)
- Surface: White / Dark surface

### Typography
- Font: Work Sans
- Display: Bold headings
- Body: Regular weight

### Components
- Cards with soft shadows
- Rounded corners (12-16px)
- Mobile-first responsive design
