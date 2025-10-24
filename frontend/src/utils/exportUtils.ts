/**
 * Document Export Utility
 * 将富文本内容导出为 Word 文档
 */

import { Document, Paragraph, TextRun, HeadingLevel, AlignmentType, Packer } from 'docx';
import { saveAs } from 'file-saver';

interface ExportOptions {
  fileName?: string;
  companyName?: string;
  date?: string;
}

/**
 * 将 HTML 内容转换为 docx 段落
 * 简化版本，支持基本格式
 */
function htmlToDocxParagraphs(htmlContent: string): Paragraph[] {
  const parser = new DOMParser();
  const doc = parser.parseFromString(htmlContent, 'text/html');
  const paragraphs: Paragraph[] = [];

  // 遍历所有子节点
  const processNode = (node: Node): void => {
    if (node.nodeType === Node.ELEMENT_NODE) {
      const element = node as HTMLElement;
      const tagName = element.tagName.toLowerCase();

      switch (tagName) {
        case 'h1':
          paragraphs.push(
            new Paragraph({
              text: element.textContent || '',
              heading: HeadingLevel.HEADING_1,
              spacing: { before: 400, after: 200 },
            })
          );
          break;

        case 'h2':
          paragraphs.push(
            new Paragraph({
              text: element.textContent || '',
              heading: HeadingLevel.HEADING_2,
              spacing: { before: 300, after: 150 },
            })
          );
          break;

        case 'h3':
          paragraphs.push(
            new Paragraph({
              text: element.textContent || '',
              heading: HeadingLevel.HEADING_3,
              spacing: { before: 200, after: 100 },
            })
          );
          break;

        case 'p':
          const textRuns: TextRun[] = [];
          element.childNodes.forEach((child) => {
            if (child.nodeType === Node.TEXT_NODE) {
              textRuns.push(new TextRun(child.textContent || ''));
            } else if (child.nodeType === Node.ELEMENT_NODE) {
              const childEl = child as HTMLElement;
              const childTag = childEl.tagName.toLowerCase();
              
              if (childTag === 'strong') {
                textRuns.push(new TextRun({ text: childEl.textContent || '', bold: true }));
              } else if (childTag === 'em') {
                textRuns.push(new TextRun({ text: childEl.textContent || '', italics: true }));
              } else if (childTag === 'u') {
                textRuns.push(new TextRun({ text: childEl.textContent || '', underline: {} }));
              } else {
                textRuns.push(new TextRun(childEl.textContent || ''));
              }
            }
          });

          paragraphs.push(
            new Paragraph({
              children: textRuns.length > 0 ? textRuns : [new TextRun(element.textContent || '')],
              spacing: { after: 120 },
            })
          );
          break;

        case 'ul':
        case 'ol':
          element.querySelectorAll('li').forEach((li) => {
            paragraphs.push(
              new Paragraph({
                text: li.textContent || '',
                bullet: tagName === 'ul' ? { level: 0 } : undefined,
                numbering: tagName === 'ol' ? { reference: 'default-numbering', level: 0 } : undefined,
                spacing: { after: 80 },
              })
            );
          });
          break;

        default:
          // 递归处理子节点
          element.childNodes.forEach(processNode);
          break;
      }
    }
  };

  // 处理 body 下的所有子节点
  doc.body.childNodes.forEach(processNode);

  return paragraphs;
}

/**
 * 导出投资备忘录为 Word 文档
 */
export async function exportIMAsWord(
  htmlContent: string,
  options: ExportOptions = {}
): Promise<void> {
  const {
    fileName = 'Investment_Memo.docx',
    companyName = '项目公司',
    date = new Date().toLocaleDateString('zh-CN'),
  } = options;

  try {
    // 转换 HTML 为段落
    const paragraphs = htmlToDocxParagraphs(htmlContent);

    // 创建文档
    const doc = new Document({
      sections: [
        {
          properties: {},
          children: [
            // 标题页
            new Paragraph({
              text: '投资备忘录',
              heading: HeadingLevel.TITLE,
              alignment: AlignmentType.CENTER,
              spacing: { after: 200 },
            }),
            new Paragraph({
              text: companyName,
              alignment: AlignmentType.CENTER,
              spacing: { after: 100 },
            }),
            new Paragraph({
              text: `分析日期: ${date}`,
              alignment: AlignmentType.CENTER,
              spacing: { after: 400 },
            }),
            new Paragraph({
              text: '━'.repeat(50),
              alignment: AlignmentType.CENTER,
              spacing: { after: 400 },
            }),
            // 正文内容
            ...paragraphs,
          ],
        },
      ],
      numbering: {
        config: [
          {
            reference: 'default-numbering',
            levels: [
              {
                level: 0,
                format: 'decimal',
                text: '%1.',
                alignment: AlignmentType.LEFT,
              },
            ],
          },
        ],
      },
    });

    // 生成并下载
    const blob = await Packer.toBlob(doc);
    saveAs(blob, fileName);
  } catch (error) {
    console.error('导出 Word 文档失败:', error);
    throw new Error('导出失败，请检查内容格式');
  }
}

/**
 * 导出为纯文本（备用方案）
 */
export function exportAsText(htmlContent: string, fileName: string = 'Investment_Memo.txt'): void {
  const parser = new DOMParser();
  const doc = parser.parseFromString(htmlContent, 'text/html');
  const text = doc.body.textContent || '';
  
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  saveAs(blob, fileName);
}
