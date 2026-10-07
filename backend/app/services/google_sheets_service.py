"""
Google Sheets Universal Marketing Reporting Service
===================================================
Tự động đồng bộ link tất cả các bài đăng thành công (Website WordPress,
Facebook Fanpage, Facebook Group Seeding) vào Google Spreadsheet chung
để phục vụ báo cáo và đánh giá hiệu quả hàng tháng.
Hỗ trợ đa thương hiệu: DAFA Glass & DAKIFA Logistics trên cùng 1 Sheet.
"""

import json
import datetime
import time
from typing import Optional, Dict, Any, List
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError
from app.models import Post, ContentPlan, Campaign, SeedingTask, SeedingCampaign, SeedingAccount, IntegrationSetting

DEFAULT_BRAND = "DAFA Glass"


class GoogleSheetsService:
    """Service tương tác với Google Sheets API v4 cho toàn bộ báo cáo bài đăng."""

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    HEADERS = [
        'STT',
        'Thời gian đăng',
        'Thương hiệu',
        'Kênh / Nền tảng',
        'Tiêu đề / Nội dung',
        'Link bài đăng (URL)',
        'Nguồn / Tài khoản',
        'Chiến dịch',
        'Định dạng'
    ]

    def __init__(self, credentials_json: str, spreadsheet_id: str, brand_name: str = DEFAULT_BRAND):
        """Khởi tạo Google Sheets Service với Service Account JSON và Spreadsheet ID."""
        self.spreadsheet_id = spreadsheet_id.strip()
        self.brand_name = brand_name
        self._sheets_cache: Dict[str, int] = {}
        try:
            creds_dict = json.loads(credentials_json)
            self.credentials = Credentials.from_service_account_info(
                creds_dict, scopes=self.SCOPES
            )
            self.service = build('sheets', 'v4', credentials=self.credentials, cache_discovery=False)
            self.sheet = self.service.spreadsheets()
        except Exception as e:
            print(f"[SHEETS ERROR] Lỗi khởi tạo Google Sheets Service: {e}")
            raise

    def _execute_with_retry(self, request, max_retries: int = 5, initial_delay: float = 3.0):
        """Thực thi Google Sheets request với exponential backoff khi gặp rate limit 429."""
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                return request.execute()
            except Exception as e:
                err_str = str(e)
                if "RATE_LIMIT_EXCEEDED" in err_str or "429" in err_str or "Quota exceeded" in err_str:
                    if attempt < max_retries - 1:
                        print(f"[SHEETS] Quota limit 429 gặp phải, đang backoff chờ {delay:.1f}s (thử lại {attempt+1}/{max_retries})...")
                        time.sleep(delay)
                        delay *= 2
                        continue
                raise e

    def _load_sheets_cache(self, force_refresh: bool = False) -> Dict[str, int]:
        """Tải danh sách sheet title -> sheetId vào bộ nhớ cache để giảm tối đa API call."""
        if not self._sheets_cache or force_refresh:
            try:
                spreadsheet = self._execute_with_retry(
                    self.sheet.get(spreadsheetId=self.spreadsheet_id, fields="sheets(properties(sheetId,title))")
                )
                self._sheets_cache = {
                    s.get('properties', {}).get('title', ''): s.get('properties', {}).get('sheetId', 0)
                    for s in spreadsheet.get('sheets', [])
                }
            except Exception as e:
                print(f"[SHEETS ERROR] Lỗi tải sheets metadata: {e}")
        return self._sheets_cache

    def ensure_monthly_sheet(self, month_year: str) -> int:
        """
        Đảm bảo tab theo tháng tồn tại (VD: 'Tháng 09/2026').
        Dùng cache để tránh gọi API lặp lại.
        """
        cache = self._load_sheets_cache()
        if month_year in cache:
            return cache[month_year]

        try:
            # Tạo sheet mới với dòng đầu được đóng băng (freeze)
            requests = [
                {
                    "addSheet": {
                        "properties": {
                            "title": month_year,
                            "gridProperties": {
                                "frozenRowCount": 1
                            }
                        }
                    }
                }
            ]
            response = self._execute_with_retry(
                self.sheet.batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': requests}
                )
            )
            
            sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
            self._sheets_cache[month_year] = sheet_id

            # Ghi tiêu đề cột 9 cột
            header_range = f"'{month_year}'!A1:I1"
            self._execute_with_retry(
                self.sheet.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=header_range,
                    valueInputOption='RAW',
                    body={'values': [self.HEADERS]}
                )
            )

            # Định dạng tiêu đề: Nền xanh Google (#1a73e8), chữ trắng đậm
            format_requests = [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(self.HEADERS)
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 26 / 255.0,
                                    "green": 115 / 255.0,
                                    "blue": 232 / 255.0
                                },
                                "textFormat": {
                                    "foregroundColor": {
                                        "red": 1.0,
                                        "green": 1.0,
                                        "blue": 1.0
                                    },
                                    "bold": True
                                }
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)"
                    }
                }
            ]
            
            self._execute_with_retry(
                self.sheet.batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': format_requests}
                )
            )

            return sheet_id

        except Exception as e:
            print(f"[SHEETS ERROR] Lỗi khi đảm bảo sheet tháng {month_year}: {e}")
            return -1

    def batch_append_published_rows(self, items: List[Dict[str, Any]]) -> int:
        """
        Ghi hàng loạt bài đăng thành công vào các sheet tháng tương ứng.
        Gom nhóm theo tháng để chỉ tốn 1 read + 1 write cho mỗi tháng,
        hoàn toàn loại bỏ nguy cơ rate limit 429 và loại trừ trùng lặp URL.
        """
        if not items:
            return 0

        items_by_month: Dict[str, List[Dict[str, Any]]] = {}
        for item in items:
            pub_at = item.get('published_at')
            if not pub_at:
                pub_at = datetime.datetime.now()
            elif isinstance(pub_at, str):
                try:
                    pub_at = datetime.datetime.fromisoformat(pub_at)
                except Exception:
                    pub_at = datetime.datetime.now()
            item['_dt'] = pub_at
            month_year = f"Tháng {pub_at.strftime('%m/%Y')}"
            items_by_month.setdefault(month_year, []).append(item)

        total_synced = 0

        for month_year, month_items in items_by_month.items():
            try:
                self.ensure_monthly_sheet(month_year)
                
                # Đọc các dòng đã có trong tab tháng để lấy STT và danh sách URLs
                range_name = f"'{month_year}'!A:F"
                result = self._execute_with_retry(
                    self.sheet.values().get(spreadsheetId=self.spreadsheet_id, range=range_name)
                )
                existing_rows = result.get('values', [])
                
                existing_urls = set()
                for r in existing_rows[1:]:
                    if len(r) > 5 and r[5]:
                        existing_urls.add(r[5].strip())

                next_stt = len(existing_rows) if len(existing_rows) > 0 else 1

                rows_to_insert = []
                for it in month_items:
                    url = (it.get('url') or '').strip()
                    if url and url in existing_urls:
                        continue  # Không ghi trùng bài đã có

                    stt = next_stt + len(rows_to_insert)
                    pub_at = it['_dt']
                    time_str = pub_at.strftime('%d/%m/%Y %H:%M')
                    brand = it.get('brand') or self.brand_name
                    channel = it.get('channel', 'Khác')
                    title = it.get('title', '')
                    source = it.get('source', 'N/A')
                    campaign_name = it.get('campaign_name', 'N/A')
                    post_format = it.get('format', '')

                    rows_to_insert.append([
                        stt,
                        time_str,
                        brand,
                        channel,
                        title,
                        url,
                        source,
                        campaign_name,
                        post_format
                    ])
                    if url:
                        existing_urls.add(url)

                if rows_to_insert:
                    self._execute_with_retry(
                        self.sheet.values().append(
                            spreadsheetId=self.spreadsheet_id,
                            range=f"'{month_year}'!A1",
                            valueInputOption='USER_ENTERED',
                            insertDataOption='INSERT_ROWS',
                            body={'values': rows_to_insert}
                        )
                    )
                    total_synced += len(rows_to_insert)
                    print(f"[SHEETS] ✅ Đã ghi thành công {len(rows_to_insert)} bài vào '{month_year}'")

                time.sleep(1.0)  # Giãn cách 1s giữa các tháng

            except Exception as e:
                print(f"[SHEETS ERROR] Lỗi ghi theo lô cho '{month_year}': {e}")

        return total_synced

    def append_published_row(self, data: Dict[str, Any]) -> bool:
        """
        Ghi một bài đăng riêng lẻ (dành cho hook thời gian thực khi đăng bài mới).
        Sử dụng batch_append_published_rows để đảm bảo deduplication và retry.
        """
        return self.batch_append_published_rows([data]) > 0

    def update_summary_sheet(self) -> bool:
        """
        Tạo hoặc cập nhật tab 'Tổng hợp' để đánh giá hiệu quả qua các tháng.
        Đọc trực tiếp dữ liệu từ các tab tháng trên Google Sheets bằng batchGet (1 request duy nhất)
        để tổng hợp cho cả 2 thương hiệu (DAFA Glass & DAKIFA Logistics).
        """
        try:
            summary_title = "Tổng hợp"
            cache = self._load_sheets_cache(force_refresh=True)
            
            sheet_id = cache.get(summary_title)
            month_sheets = [t for t in cache.keys() if t.startswith('Tháng ')]
            
            if sheet_id is None:
                req = {
                    "addSheet": {
                        "properties": {
                            "title": summary_title,
                            "gridProperties": {"frozenRowCount": 1}
                        }
                    }
                }
                res = self._execute_with_retry(
                    self.sheet.batchUpdate(spreadsheetId=self.spreadsheet_id, body={'requests': [req]})
                )
                sheet_id = res['replies'][0]['addSheet']['properties']['sheetId']
                self._sheets_cache[summary_title] = sheet_id
            else:
                self._execute_with_retry(
                    self.sheet.values().clear(
                        spreadsheetId=self.spreadsheet_id,
                        range=f"'{summary_title}'!A1:Z500"
                    )
                )

            month_sheets = sorted(month_sheets, reverse=True)
            
            stats_by_month = {}
            for m in month_sheets:
                stats_by_month[m] = {
                    "DAFA Glass": {"Website": 0, "Fanpage": 0, "Seeding": 0, "campaigns": {}},
                    "DAKIFA Logistics": {"Website": 0, "Fanpage": 0, "Seeding": 0, "campaigns": {}},
                    "Khác": {"Website": 0, "Fanpage": 0, "Seeding": 0, "campaigns": {}}
                }

            if month_sheets:
                # Đọc tất cả các tab tháng trong DUY NHẤT 1 API request bằng batchGet
                ranges = [f"'{m}'!A2:I500" for m in month_sheets]
                batch_res = self._execute_with_retry(
                    self.sheet.values().batchGet(spreadsheetId=self.spreadsheet_id, ranges=ranges)
                )
                val_ranges = batch_res.get('valueRanges', [])
                
                for idx, vr in enumerate(val_ranges):
                    m = month_sheets[idx]
                    rows = vr.get('values', [])
                    for r in rows:
                        if len(r) < 4:
                            continue
                        brand = r[2].strip() if len(r) > 2 and r[2].strip() else "DAFA Glass"
                        if "DAKIFA" in brand.upper():
                            brand_key = "DAKIFA Logistics"
                        elif "DAFA" in brand.upper():
                            brand_key = "DAFA Glass"
                        else:
                            brand_key = "Khác"
                            
                        channel = r[3].strip() if len(r) > 3 else ""
                        camp = r[7].strip() if len(r) > 7 and r[7].strip() else "Không gắn chiến dịch"
                        
                        if "WEB" in channel.upper():
                            stats_by_month[m][brand_key]["Website"] += 1
                        elif "FANPAGE" in channel.upper():
                            stats_by_month[m][brand_key]["Fanpage"] += 1
                        elif "SEEDING" in channel.upper():
                            stats_by_month[m][brand_key]["Seeding"] += 1
                        else:
                            stats_by_month[m][brand_key]["Website"] += 1
                            
                        stats_by_month[m][brand_key]["campaigns"][camp] = stats_by_month[m][brand_key]["campaigns"].get(camp, 0) + 1

            all_rows = []
            main_headers = ['Tháng', 'Thương hiệu', 'Tổng bài đã đăng', 'Website (WordPress)', 'Fanpage (Facebook)', 'Seeding']
            all_rows.append(main_headers)

            for m in month_sheets:
                for b_name in ["DAFA Glass", "DAKIFA Logistics"]:
                    b_data = stats_by_month[m][b_name]
                    w = b_data["Website"]
                    f = b_data["Fanpage"]
                    s = b_data["Seeding"]
                    tot = w + f + s
                    if tot > 0:
                        all_rows.append([m, b_name, tot, w, f, s])

            all_rows.append([])
            all_rows.append(['--- CHI TIẾT THEO CHIẾN DỊCH ---'])
            all_rows.append(['Tháng', 'Thương hiệu', 'Chiến dịch', 'Số bài thành công'])

            for m in month_sheets:
                for b_name in ["DAFA Glass", "DAKIFA Logistics"]:
                    for c_name, c_cnt in stats_by_month[m][b_name]["campaigns"].items():
                        all_rows.append([m, b_name, c_name, c_cnt])

            self._execute_with_retry(
                self.sheet.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"'{summary_title}'!A1",
                    valueInputOption='USER_ENTERED',
                    body={'values': all_rows}
                )
            )

            fmt_reqs = [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(main_headers)
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 26 / 255.0,
                                    "green": 115 / 255.0,
                                    "blue": 232 / 255.0
                                },
                                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True}
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)"
                    }
                }
            ]
            self._execute_with_retry(
                self.sheet.batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': fmt_reqs}
                )
            )

            print("[SHEETS] ✅ Đã cập nhật tab 'Tổng hợp' thành công!")
            return True

        except Exception as e:
            print(f"[SHEETS ERROR] Lỗi khi cập nhật tab Tổng hợp: {e}")
            return False

    def sync_all_history(self, db, clear_existing_sheets: bool = False) -> Dict[str, Any]:
        """
        Đồng bộ toàn bộ lịch sử các bài đã đăng thành công từ trước tới nay vào Google Sheets.
        Sử dụng batch append tối ưu để hoàn thành trong 2-3 API call.
        """
        if clear_existing_sheets:
            try:
                cache = self._load_sheets_cache(force_refresh=True)
                for t in list(cache.keys()):
                    if t.startswith('Tháng '):
                        self._execute_with_retry(
                            self.sheet.values().clear(
                                spreadsheetId=self.spreadsheet_id,
                                range=f"'{t}'!A2:Z500"
                            )
                        )
                        self._execute_with_retry(
                            self.sheet.values().update(
                                spreadsheetId=self.spreadsheet_id,
                                range=f"'{t}'!A1:I1",
                                valueInputOption='RAW',
                                body={'values': [self.HEADERS]}
                            )
                        )
            except Exception as e:
                print(f"[SHEETS] Lỗi khi làm sạch sheets: {e}")

        items = []

        # 1. Đồng bộ bài viết Website & Fanpage
        posts = db.query(Post).filter(
            Post.status == "Published",
            Post.published_url.isnot(None),
            Post.published_url != ""
        ).order_by(Post.published_at.asc()).all()

        for p in posts:
            plan = p.content_plan
            platform = (plan.platform if plan else "Web") or "Web"
            channel_name = "Fanpage (Facebook)" if platform.lower() == "fanpage" else "Website (WordPress)"
            campaign_name = plan.campaign.name if (plan and plan.campaign) else "N/A"
            post_format = plan.format if plan else "Long article"
            source = f"{self.brand_name} Fanpage" if platform.lower() == "fanpage" else "dafaglass.com"

            items.append({
                "published_at": p.published_at or (p.content_plan.created_at if p.content_plan else datetime.datetime.now()),
                "brand": self.brand_name,
                "channel": channel_name,
                "title": p.title or "",
                "url": p.published_url,
                "source": source,
                "campaign_name": campaign_name,
                "format": post_format
            })

        # 2. Đồng bộ task Seeding thành công (nếu có model SeedingTask)
        try:
            seeding_tasks = db.query(SeedingTask).filter(
                SeedingTask.status == "success"
            ).order_by(SeedingTask.executed_at.asc()).all()

            for st in seeding_tasks:
                scamp = db.query(SeedingCampaign).filter(SeedingCampaign.id == st.campaign_id).first()
                camp_name = scamp.name if scamp else "N/A"
                
                sacc = db.query(SeedingAccount).filter(SeedingAccount.id == st.account_id).first() if st.account_id else None
                source = sacc.username if sacc else "Via Seeding"

                type_labels = {
                    "POST_GROUP": "Seeding (Hội nhóm)",
                    "COMMENT": "Seeding (Comment dạo)",
                    "REPLY_COMMENT": "Seeding (Trả lời comment)"
                }
                channel_label = type_labels.get(st.task_type, f"Seeding ({st.task_type})")

                items.append({
                    "published_at": st.executed_at or st.created_at,
                    "brand": self.brand_name,
                    "channel": channel_label,
                    "title": (st.generated_content[:80] + "...") if st.generated_content else "N/A",
                    "url": st.target_url,
                    "source": source,
                    "campaign_name": camp_name,
                    "format": st.task_type
                })
        except Exception:
            pass

        # Thực hiện ghi theo lô
        synced_count = self.batch_append_published_rows(items)

        time.sleep(1.5)
        # Cập nhật tab tổng hợp
        self.update_summary_sheet()

        return {
            "status": "success",
            "synced_count": synced_count,
            "brand": self.brand_name,
            "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"
        }


# ============================================================
# HELPER FUNCTIONS CHO TOÀN BỘ HỆ THỐNG
# ============================================================

def get_google_sheets_service(db, require_active: bool = False, brand_name: str = DEFAULT_BRAND) -> Optional[GoogleSheetsService]:
    """Lấy GoogleSheetsService từ cấu hình trong database."""
    try:
        query = db.query(IntegrationSetting).filter(
            IntegrationSetting.platform == 'GoogleSheets'
        )
        if require_active:
            active_setting = query.filter(IntegrationSetting.is_active == True).first()
            if active_setting and active_setting.access_token and active_setting.url:
                return GoogleSheetsService(active_setting.access_token, active_setting.url, brand_name=brand_name)
            
        # Fallback: nếu require_active không tìm thấy nhưng có cấu hình đã nhập đầy đủ token và URL
        setting = db.query(IntegrationSetting).filter(IntegrationSetting.platform == 'GoogleSheets').first()
        if not setting or not setting.access_token or not setting.url:
            return None
            
        return GoogleSheetsService(setting.access_token, setting.url, brand_name=brand_name)
    except Exception as e:
        print(f"[SHEETS] Không thể khởi tạo Google Sheets service: {e}")
        return None


def sync_published_post_to_sheets(post: Post, db, brand_name: str = DEFAULT_BRAND) -> bool:
    """
    Hook tự động: Gọi khi một bài viết Website hoặc Fanpage được xuất bản thành công.
    """
    try:
        svc = get_google_sheets_service(db, require_active=True, brand_name=brand_name)
        if not svc:
            return False

        if not post.published_url:
            return False

        plan = post.content_plan
        platform = (plan.platform if plan else "Web") or "Web"
        channel_name = "Fanpage (Facebook)" if platform.lower() == "fanpage" else "Website (WordPress)"
        campaign_name = plan.campaign.name if (plan and plan.campaign) else "N/A"
        post_format = plan.format if plan else "Long article"
        source = f"{brand_name} Fanpage" if platform.lower() == "fanpage" else "Website"

        success = svc.append_published_row({
            "published_at": post.published_at or datetime.datetime.now(),
            "brand": brand_name,
            "channel": channel_name,
            "title": post.title or "",
            "url": post.published_url,
            "source": source,
            "campaign_name": campaign_name,
            "format": post_format
        })
        
        if success:
            svc.update_summary_sheet()
            
        return success
    except Exception as e:
        print(f"[SHEETS] Lỗi auto-sync bài đăng: {e}")
        return False


def sync_seeding_task_to_sheets(task: SeedingTask, db, brand_name: str = DEFAULT_BRAND) -> bool:
    """
    Hook tự động: Gọi khi một task seeding chạy thành công.
    """
    try:
        if task.status != "success":
            return False

        svc = get_google_sheets_service(db, require_active=True, brand_name=brand_name)
        if not svc:
            return False

        scamp = db.query(SeedingCampaign).filter(SeedingCampaign.id == task.campaign_id).first()
        camp_name = scamp.name if scamp else "N/A"
        
        sacc = db.query(SeedingAccount).filter(SeedingAccount.id == task.account_id).first() if task.account_id else None
        source = sacc.username if sacc else "Via Seeding"

        type_labels = {
            "POST_GROUP": "Seeding (Hội nhóm)",
            "COMMENT": "Seeding (Comment dạo)",
            "REPLY_COMMENT": "Seeding (Trả lời comment)"
        }
        channel_label = type_labels.get(task.task_type, f"Seeding ({task.task_type})")

        success = svc.append_published_row({
            "published_at": task.executed_at or datetime.datetime.now(),
            "brand": brand_name,
            "channel": channel_label,
            "title": (task.generated_content[:80] + "...") if task.generated_content else "N/A",
            "url": task.target_url,
            "source": source,
            "campaign_name": camp_name,
            "format": task.task_type or "POST_GROUP"
        })
        
        if success:
            svc.update_summary_sheet()
            
        return success
    except Exception as e:
        print(f"[SHEETS] Lỗi auto-sync seeding task: {e}")
        return False
