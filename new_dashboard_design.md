# Algo Trading Dashboard - UI Product Requirements

## Overview
A minimal, mobile-first dashboard for monitoring algorithmic stock trading activity. Single-page, scrollable layout optimized for personal use on mobile devices.

---

## Layout Structure

### Page Container
- **Background**: Light gray (`#F9FAFB`)
- **Content width**: Maximum 896px (4xl), centered with horizontal padding
- **Padding**: 16px horizontal on mobile
- **Vertical spacing**: 24px between all major sections

---

## Header Component

### Structure
- **Position**: Sticky to top of viewport
- **Background**: White with bottom border
- **Border**: 1px solid light gray (`#E5E7EB`)
- **Height**: Auto, with 16px vertical padding
- **Z-index**: 10 (stays above scrolling content)

### Elements
- **Title**: "Algo Trading"
  - Font size: 20px
  - Font weight: Semibold
  - Color: Dark gray (`#111827`)
  - Alignment: Left
  
- **Refresh Button**
  - Position: Right aligned
  - Icon: Circular arrow/refresh icon (20px)
  - Interactive state: Light gray background on hover
  - Padding: 8px
  - Border radius: Full circle

---

## Section 1: System Health

### Container
- **Background**: White
- **Border**: 1px solid light gray (`#E5E7EB`)
- **Border radius**: 8px
- **Padding**: 16px
- **Margin bottom**: 24px

### Header
- **Icon**: Activity/pulse icon (20px) in dark gray
- **Title**: "System Health"
  - Font size: 18px
  - Font weight: Semibold
  - Spacing: 8px gap between icon and text
- **Margin bottom**: 12px

### Content Grid
- **Layout**: 2-column grid
- **Gap**: 12px between items
- **Items**: 4 status indicators

### Status Item Format
Each item displays:
- **Label**: 
  - Font size: 12px
  - Color: Medium gray (`#6B7280`)
  - Margin bottom: 2px
  
- **Value**:
  - Font size: 14px
  - Font weight: Medium
  - Color: Dark gray (`#111827`) for timestamps
  - Color: Green (`#16A34A`) for healthy/connected statuses
  - Text transform: Capitalize for status words

### Status Items
1. Last Data Sync (timestamp)
2. Last Algo Run (timestamp)
3. Database (status with color indicator)
4. Alpaca API (status with color indicator)

---

## Section 2: Account Balance

### Container
- **Background**: White
- **Border**: 1px solid light gray (`#E5E7EB`)
- **Border radius**: 8px
- **Padding**: 16px
- **Margin bottom**: 24px

### Header
- **Icon**: Dollar sign icon (20px) in dark gray
- **Title**: "Account Balance"
  - Font size: 18px
  - Font weight: Semibold
  - Spacing: 8px gap between icon and text
- **Margin bottom**: 12px

### Primary Metrics
Each metric displayed as horizontal row with space-between alignment:

1. **Total Funds**
   - Label: 14px, medium gray, regular weight
   - Value: 32px, dark gray, bold weight
   - Margin bottom: 12px

2. **Invested**
   - Label: 14px, medium gray, regular weight
   - Value: 18px, dark gray, medium weight
   - Margin bottom: 12px

3. **Cash Available**
   - Label: 14px, medium gray, regular weight
   - Value: 18px, dark gray, medium weight
   - Margin bottom: 12px

### Returns Section
- **Separator**: 1px border-top, light gray, 12px padding above
- **Section label**: "Returns"
  - Font size: 12px
  - Color: Medium gray
  - Margin bottom: 8px

- **Layout**: 3-column grid with 8px gap
- **Column items**: WoW, MoM, YoY

### Return Item Format
- **Label**: 
  - Font size: 12px
  - Color: Medium gray
  
- **Value**:
  - Font size: 14px
  - Font weight: Semibold
  - Color: Green (`#16A34A`) for positive values
  - Color: Red (`#DC2626`) for negative values
  - Format: Include + or - prefix, followed by percentage with 2 decimals

---

## Section 3: Current Positions

### Container
- **Background**: White
- **Border**: 1px solid light gray (`#E5E7EB`)
- **Border radius**: 8px
- **Padding**: 16px
- **Margin bottom**: 24px

### Header
- **Title**: "Current Positions"
  - Font size: 18px
  - Font weight: Semibold
  - Color: Dark gray
  - Margin bottom: 12px

### Position List
- **Spacing**: 12px between items
- **Separator**: 1px border-bottom on all items except last
- **Padding bottom**: 12px per item (0 on last)

### Position Item Layout
Each position displays in two rows:

**Row 1: Stock symbol and unrealized gains**
- Left side:
  - Symbol: Font size 14px, semibold, dark gray
  - Invested amount: Font size 12px, medium gray, below symbol
  
- Right side (right-aligned):
  - Unrealized percentage: Font size 14px, semibold
    - Green for positive, red for negative
    - Format: +/-X.XX%
  - Unrealized dollar amount: Font size 12px, below percentage
    - Green for positive, red for negative
    - Format: +/-$X,XXX.XX

**Row 2: Price comparison**
- Layout: Space-between horizontal
- Font size: 12px
- Color: Medium gray
- Left: "Entry: $XXX.XX"
- Right: "Current: $XXX.XX"

---

## Section 4: Recent Trades

### Container
- **Background**: White
- **Border**: 1px solid light gray (`#E5E7EB`)
- **Border radius**: 8px
- **Padding**: 16px
- **Margin bottom**: 24px (extra bottom margin for page end)

### Header
- **Title**: "Recent Trades"
  - Font size: 18px
  - Font weight: Semibold
  - Color: Dark gray
  - Margin bottom: 12px

### Trade List
- **Spacing**: 8px between items
- **Separator**: 1px border-bottom on all items except last
- **Padding vertical**: 8px per item

### Trade Item Layout
Horizontal layout with space-between alignment:

**Left side: Trade info**
- **Icon container**:
  - Size: 24px × 24px
  - Border radius: 4px
  - Background: Light green (`#F0FDF4`) for buys, Light red (`#FEF2F2`) for sells
  - Icon: Up arrow (green `#16A34A`) for buy, Down arrow (red `#DC2626`) for sell
  - Icon size: 16px
  
- **Text container** (next to icon, 12px gap):
  - Symbol: Font size 14px, semibold, dark gray
  - Timestamp: Font size 12px, medium gray, below symbol

**Right side: Price info** (right-aligned)
- Price: Font size 14px, medium weight, dark gray
- Quantity: Font size 12px, medium gray, below price
- Format: "×XX"

---

## Color Palette

### Primary Colors
- **Background**: `#F9FAFB` (light gray)
- **Card background**: `#FFFFFF` (white)
- **Border**: `#E5E7EB` (light gray)

### Text Colors
- **Primary text**: `#111827` (dark gray)
- **Secondary text**: `#6B7280` (medium gray)
- **Positive values**: `#16A34A` (green)
- **Negative values**: `#DC2626` (red)

### Status Colors
- **Healthy/Connected**: `#16A34A` (green)
- **Buy indicator background**: `#F0FDF4` (light green)
- **Sell indicator background**: `#FEF2F2` (light red)

---

## Typography

### Font Sizes
- **Page title**: 20px (1.25rem)
- **Section headers**: 18px (1.125rem)
- **Primary values**: 32px (2rem) for total funds only
- **Secondary values**: 18px (1.125rem)
- **Body text**: 14px (0.875rem)
- **Labels/small text**: 12px (0.75rem)

### Font Weights
- **Bold**: 700 (total funds only)
- **Semibold**: 600 (section headers, symbols, percentages)
- **Medium**: 500 (most values)
- **Regular**: 400 (labels, descriptions)

---

## Responsive Behavior

### Mobile (< 768px)
- Full width with 16px horizontal padding
- Single column layout (already optimized)
- Touch targets minimum 44px × 44px

### Tablet/Desktop (≥ 768px)
- Content container max-width: 896px
- Centered with auto margins
- Same vertical layout maintained
- Increased horizontal padding: 24px

---

## Interactive States

### Buttons
- **Default**: Transparent or light background
- **Hover**: Light gray background (`#F3F4F6`)
- **Active/Press**: Slightly darker gray (`#E5E7EB`)
- **Transition**: 150ms ease

### Cards
- No hover state (informational only)
- No click/tap interaction

---

## Data Formatting Rules

### Currency
- Format: `$XX,XXX.XX`
- Always show 2 decimal places
- Include thousands separator (comma)
- Use Intl.NumberFormat for consistency

### Percentages
- Format: `+/-X.XX%`
- Always show sign (+ or -)
- Always show 2 decimal places
- No space between number and %

### Stock Prices
- Format: `$XXX.XX`
- Always show 2 decimal places
- No thousands separator needed for typical stock prices

### Timestamps
- Prefer relative format: "X min/hours/days ago"
- Keep concise for mobile readability

### Status Text
- Capitalize first letter
- Use concise terms: "healthy", "connected", "error"

---

## Accessibility Notes

- Minimum font size: 12px for readability
- Color coding supplemented with text labels
- Sufficient contrast ratios (WCAG AA minimum)
- Touch targets at least 44px for interactive elements
- Semantic HTML structure for screen readers

---

## Future Considerations (Not in MVP)

- Dark mode color scheme
- Pull-to-refresh gesture
- Expandable position details
- Filtering/sorting options
- Historical performance chart
- Trade execution controls