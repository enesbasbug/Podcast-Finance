// Renders docs/cover.jpg (3000x3000) for the podcast. Run: swift scripts/make_cover.swift
import AppKit

let size = 3000.0
let out = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 3000, pixelsHigh: 3000, bitsPerSample: 8,
                           samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                           bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: out)
let ctx = NSGraphicsContext.current!.cgContext

// Background: deep navy gradient
let grad = NSGradient(colors: [NSColor(red: 0.04, green: 0.09, blue: 0.20, alpha: 1),
                               NSColor(red: 0.02, green: 0.30, blue: 0.36, alpha: 1)])!
grad.draw(in: NSRect(x: 0, y: 0, width: size, height: size), angle: 60)

// Rising line chart motif
ctx.setStrokeColor(NSColor(red: 0.35, green: 0.95, blue: 0.70, alpha: 1).cgColor)
ctx.setLineWidth(42); ctx.setLineJoin(.round); ctx.setLineCap(.round)
let pts: [(Double, Double)] = [(300, 900), (750, 1150), (1100, 1000), (1500, 1450), (1900, 1300), (2300, 1750), (2700, 1950)]
ctx.move(to: CGPoint(x: pts[0].0, y: pts[0].1))
for p in pts.dropFirst() { ctx.addLine(to: CGPoint(x: p.0, y: p.1)) }
ctx.strokePath()
ctx.setFillColor(NSColor(red: 0.35, green: 0.95, blue: 0.70, alpha: 1).cgColor)
ctx.fillEllipse(in: CGRect(x: 2700 - 70, y: 1950 - 70, width: 140, height: 140))

func draw(_ s: String, font: NSFont, color: NSColor, y: Double, kern: Double = 0) {
    let attrs: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: color, .kern: kern]
    let str = NSAttributedString(string: s, attributes: attrs)
    let w = str.size().width
    str.draw(at: NSPoint(x: (size - w) / 2, y: y))
}
let white = NSColor.white
draw("THE WEEKLY", font: NSFont(name: "Futura-Bold", size: 300)!, color: white, y: 2450, kern: 20)
draw("MARKET BRIEF", font: NSFont(name: "Futura-Bold", size: 300)!, color: white, y: 2130, kern: 20)
draw("Markets · Earnings · The week ahead", font: NSFont(name: "Futura-Medium", size: 120)!,
     color: NSColor(white: 1, alpha: 0.8), y: 520)
draw("EVERY MONDAY · UK EDITION", font: NSFont(name: "Futura-Bold", size: 110)!,
     color: NSColor(red: 0.35, green: 0.95, blue: 0.70, alpha: 1), y: 300, kern: 12)
NSGraphicsContext.restoreGraphicsState()
let jpg = out.representation(using: .jpeg, properties: [.compressionFactor: 0.85])!
try! jpg.write(to: URL(fileURLWithPath: "docs/cover.jpg"))
print("wrote docs/cover.jpg")
