import fitz  # PyMuPDF
import m09get_whr as m09

def get_Po_Zs(pdf_document,xra,yra):
    """
    PDF ドキュメント内の各ページに対して、ズーム倍率付きの (x, y, z) 座標を取得します。

    - z 座標は、A4 横 (幅 210 mm) または A4 縦 (高さ 297 mm) を基準とした倍率を基に、
      ページサイズに xra, yra をかけた最小値を使用して算出されます。
    - x, y 座標はページの回転角 (0, 90, 180, 270 度) に基づき、ページの表示位置を
      PDF 単位（ポイント）で決定します。
    - 単位変換には、1インチ = 25.4mm、1インチ = 72pt を使用します。

    Args:
        pdf_document (fitz.Document): 対象の PDF ドキュメント。
        xra (float): ページ幅方向の倍率。
        yra (float): ページ高さ方向の倍率。

    Returns:
        dict: 各ページ番号（1始まり）をキーとし、(x, y, z) のタプルを値とする辞書。
              例: {1: (0.0, 0.0, 0.75), 2: (0.0, 841.89, 0.72), ...}

    Raises:
        ValueError: 回転角度が 0, 90, 180, 270 のいずれでもない場合。
    """
    print("　ページ番号をキーとしてズームする座標X,yとズーム倍率) のタプルを値とする辞書として取得しています。")
    whr=m09.get_pdf_page_xyr(pdf_document)

    points = {}

    for page, (width, height, rotation) in whr.items():
        # 条件に基づいて (x, y, z) を決定 
        #z = 210 / height # 奇しくもこれで、大画面では高さが合うようになっている。
        z = min((330/width)*xra,(210/height)*yra)
        # mm を PDF 単位 (pt) に変換 (1 inch = 25.4 mm, 1 inch = 72 pt)
        width_pt = width / 25.4 * 72
        height_pt = height / 25.4 * 72
        if rotation == 0:
            x, y = 0.0, 0.0
        elif rotation == 90:
            x, y = 0.0, height_pt
        elif rotation == 180:
            x, y = width_pt, height_pt
        elif rotation == 270:
            x, y = height_pt, 0.0
        else:
            raise ValueError("Invalid rotation value. Expected 0, 90, 180, or 270.")
        points[page] = (x, y, z)
        #print(f"Page {page}: x = {x:.2f},xra={xra:.2f}, y = {y:.2f},yratio={yra:.2f}, z = {z:.2f}　,横幅:{width_pt},縦幅:{height_pt}")
    return points

if __name__ == "__main__":
    pdf_document = fitz.open(r"c:\Users\uboni\Desktop\検査用栞付結合データ.pdf")
    points = get_Po_Zs(pdf_document,1.0,1.0)

    # 結果を表示
    #for page, (x, y, z) in points.items():
    #    print(f"Page {page}: x = {x:.2f}, y = {y:.2f}, z = {z:.2f}")
    #print(pdf_document.get_toc())