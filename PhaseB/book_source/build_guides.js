const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  PageBreak, TableOfContents, Header, Footer, PageNumber, ImageRun,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  LevelFormat, convertInchesToTwip
} = require("docx");

// __dirname = PhaseB/book_source/; project root is two levels up.
const PROJECT_ROOT = path.join(__dirname, "..", "..");

const FONT = "Calibri";
const SIZE = 24; // 12pt in half points

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 200, line: 276 },
    children: [new TextRun({ text, font: FONT, size: SIZE, ...opts })],
    ...opts.paragraphOpts,
  });
}
function para(children, paragraphOpts = {}) {
  return new Paragraph({ spacing: { after: 200, line: 276 }, children, ...paragraphOpts });
}
function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 400, after: 200 }, children: [new TextRun({ text, font: FONT })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 300, after: 150 }, children: [new TextRun({ text, font: FONT })] });
}
function h3(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 100 }, children: [new TextRun({ text, font: FONT, italics: true })] });
}
function bullet(text, level = 0) {
  return new Paragraph({
    spacing: { after: 120, line: 276 },
    bullet: { level },
    children: [new TextRun({ text, font: FONT, size: SIZE })],
  });
}
function code(text) {
  return new Paragraph({
    spacing: { before: 100, after: 200 },
    shading: { type: ShadingType.CLEAR, fill: "F2F2F2" },
    children: [new TextRun({ text, font: "Consolas", size: 20 })],
  });
}
function note(text) {
  return new Paragraph({
    spacing: { before: 100, after: 200 },
    shading: { type: ShadingType.CLEAR, fill: "E8F0FE" },
    children: [new TextRun({ text: "Note: " + text, font: FONT, size: SIZE, italics: true, color: "1F2D3D" })],
  });
}
function warning(text) {
  return new Paragraph({
    spacing: { before: 100, after: 200 },
    shading: { type: ShadingType.CLEAR, fill: "FDEDED" },
    children: [new TextRun({ text: "Caution: " + text, font: FONT, size: SIZE, bold: true, color: "8A1F1F" })],
  });
}

function simpleTable(headerRow, rows, colWidths) {
  const totalWidth = 9000;
  const widths = colWidths || headerRow.map(() => Math.floor(totalWidth / headerRow.length));
  const header = new TableRow({
    tableHeader: true,
    children: headerRow.map((t, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: "1F2D3D" },
      children: [new Paragraph({ children: [new TextRun({ text: t, font: FONT, size: 20, bold: true, color: "FFFFFF" })] })],
    })),
  });
  const body = rows.map(r => new TableRow({
    children: r.map((t, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      children: [new Paragraph({ children: [new TextRun({ text: String(t), font: FONT, size: 20 })] })],
    })),
  }));
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: widths,
    rows: [header, ...body],
  });
}

const logoBuffer = fs.readFileSync(path.join(PROJECT_ROOT, "LOGO1.png"));

function coverPage(title, subtitle) {
  return [
    new Paragraph({ spacing: { before: 600, after: 400 }, alignment: AlignmentType.CENTER,
      children: [ new ImageRun({ type: "png", data: logoBuffer, transformation: { width: 380, height: 150 } }) ] }),
    new Paragraph({ spacing: { before: 800, after: 100 }, alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "FlowGrid, Capstone Project Phase B", font: FONT, size: 28, bold: true })] }),
    new Paragraph({ spacing: { before: 200, after: 100 }, alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: title, font: FONT, size: 40, bold: true, color: "1F2D3D" })] }),
    new Paragraph({ spacing: { before: 100, after: 600 }, alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: subtitle, font: FONT, size: 24, italics: true, color: "444444" })] }),
    new Paragraph({ spacing: { before: 600, after: 100 }, alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Team Code: ", font: FONT, size: SIZE, bold: true }), new TextRun({ text: "26-1-D-30", font: FONT, size: SIZE, bold: true, color: "1F2D3D" })] }),
    new Paragraph({ spacing: { after: 100 }, alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Students: ", font: FONT, size: SIZE, bold: true }), new TextRun({ text: "Avishag Levi, Einav Momi Ben Shushan", font: FONT, size: SIZE, bold: true, color: "1F2D3D" })] }),
    new Paragraph({ spacing: { after: 100 }, alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Advisor: ", font: FONT, size: SIZE, bold: true }), new TextRun({ text: "Dr. Cohen Reuven", font: FONT, size: SIZE, bold: true, color: "1F2D3D" })] }),
    new Paragraph({ spacing: { before: 400, after: 100 }, alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Git Repository: ", font: FONT, size: 20 }), new TextRun({ text: "https://github.com/einavbs1/FlowGrid", font: FONT, size: 20, color: "1F2D3D" })] }),
    new Paragraph({ spacing: { after: 100 }, alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Demo Video: ", font: FONT, size: 20 }), new TextRun({ text: "https://drive.google.com/file/d/1BE3oeGWWbVrQEC_ZL0rVh5AdPs9kDNTY/view", font: FONT, size: 20, color: "1F2D3D" })] }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

function toc() {
  return [
    h1("Table of Contents"),
    new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1 3" }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

function buildDoc(fileName, bodySections) {
  const doc = new Document({
    features: { updateFields: true },
    styles: { default: { document: { run: { font: FONT, size: SIZE } } } },
    sections: [{
      properties: {},
      headers: {
        default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "FlowGrid, Capstone Project Phase B", font: FONT, size: 16, color: "808080" })] })] }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18 })],
          })],
        }),
      },
      children: bodySections,
    }],
  });
  Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync(path.join(__dirname, "..", fileName), buffer);
    console.log("Written: " + fileName);
  });
}

module.exports = { p, para, h1, h2, h3, bullet, code, note, warning, simpleTable, coverPage, toc, buildDoc, logoBuffer, FONT, SIZE, fs, path, ImageRun, AlignmentType };
