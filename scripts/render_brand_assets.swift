import AppKit
import Foundation

let project = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : FileManager.default.currentDirectoryPath)
let iconURL = project.appendingPathComponent("AutoBlureFace_icon.png")
guard let icon = NSImage(contentsOf: iconURL) else {
    fatalError("Missing app icon: \(iconURL.path)")
}
let output = project.appendingPathComponent("assets")
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)

let dark = NSColor(calibratedRed: 0.075, green: 0.080, blue: 0.095, alpha: 1)
let panel = NSColor(calibratedRed: 0.135, green: 0.145, blue: 0.175, alpha: 1)
let orange = NSColor(calibratedRed: 0.91, green: 0.31, blue: 0.22, alpha: 1)
let white = NSColor(calibratedRed: 0.96, green: 0.97, blue: 0.99, alpha: 1)
let muted = NSColor(calibratedRed: 0.68, green: 0.71, blue: 0.77, alpha: 1)

func rounded(_ rect: NSRect, radius: CGFloat, color: NSColor) {
    color.setFill()
    NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius).fill()
}

func label(_ string: String, at point: NSPoint, size: CGFloat, weight: NSFont.Weight, color: NSColor) {
    let attributes: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: size, weight: weight),
        .foregroundColor: color
    ]
    (string as NSString).draw(at: point, withAttributes: attributes)
}

func savePNG(name: String, width: Int, height: Int, scale: CGFloat = 1, draw: () -> Void) throws {
    let bitmap = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: Int(CGFloat(width) * scale),
        pixelsHigh: Int(CGFloat(height) * scale),
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
    )!
    NSGraphicsContext.saveGraphicsState()
    let context = NSGraphicsContext(bitmapImageRep: bitmap)!
    NSGraphicsContext.current = context
    context.cgContext.scaleBy(x: scale, y: scale)
    draw()
    context.flushGraphics()
    NSGraphicsContext.restoreGraphicsState()
    let data = bitmap.representation(using: .png, properties: [:])!
    try data.write(to: output.appendingPathComponent(name))
}

try savePNG(name: "banner.png", width: 1200, height: 300) {
    rounded(NSRect(x: 0, y: 0, width: 1200, height: 300), radius: 28, color: dark)
    rounded(NSRect(x: 26, y: 26, width: 1148, height: 248), radius: 23, color: panel)
    rounded(NSRect(x: 37, y: 37, width: 9, height: 226), radius: 4, color: orange)
    icon.draw(in: NSRect(x: 74, y: 57, width: 186, height: 186), from: .zero, operation: .sourceOver, fraction: 1)
    label("FaceBlur Studio", at: NSPoint(x: 295, y: 151), size: 66, weight: .bold, color: white)
    label("Local video face blurring", at: NSPoint(x: 299, y: 104), size: 27, weight: .medium, color: muted)
    rounded(NSRect(x: 299, y: 70, width: 605, height: 5), radius: 2, color: orange)
}

try savePNG(name: "dmg-background.png", width: 720, height: 480) {
    rounded(NSRect(x: 0, y: 0, width: 720, height: 480), radius: 0, color: dark)
    NSGraphicsContext.current!.cgContext.translateBy(x: 0, y: 40)
    rounded(NSRect(x: 24, y: 286, width: 672, height: 130), radius: 24, color: panel)
    rounded(NSRect(x: 24, y: 286, width: 7, height: 130), radius: 3, color: orange)
    icon.draw(in: NSRect(x: 47, y: 303, width: 96, height: 96), from: .zero, operation: .sourceOver, fraction: 1)
    label("FaceBlur Studio", at: NSPoint(x: 159, y: 351), size: 32, weight: .bold, color: white)
    label("Drag the app to Applications", at: NSPoint(x: 161, y: 316), size: 18, weight: .medium, color: muted)

    rounded(NSRect(x: 62, y: 78, width: 236, height: 178), radius: 24, color: panel)
    rounded(NSRect(x: 422, y: 78, width: 236, height: 178), radius: 24, color: panel)
    let caption = NSColor(calibratedRed: 0.88, green: 0.90, blue: 0.94, alpha: 1)
    rounded(NSRect(x: 91, y: 82, width: 178, height: 32), radius: 12, color: caption)
    rounded(NSRect(x: 451, y: 82, width: 178, height: 32), radius: 12, color: caption)
    label("1 · APP", at: NSPoint(x: 76, y: 225), size: 13, weight: .bold, color: muted)
    label("2 · APPLICATIONS", at: NSPoint(x: 436, y: 225), size: 13, weight: .bold, color: muted)

    let arrow = NSBezierPath()
    arrow.lineWidth = 8
    arrow.lineCapStyle = .round
    arrow.lineJoinStyle = .round
    arrow.move(to: NSPoint(x: 322, y: 167))
    arrow.line(to: NSPoint(x: 395, y: 167))
    arrow.line(to: NSPoint(x: 377, y: 183))
    arrow.move(to: NSPoint(x: 395, y: 167))
    arrow.line(to: NSPoint(x: 377, y: 151))
    orange.setStroke()
    arrow.stroke()

    label("INSTALL · DRAG & DROP", at: NSPoint(x: 252, y: 26), size: 15, weight: .semibold, color: muted)
}

print("Rendered banner.png and dmg-background.png")
