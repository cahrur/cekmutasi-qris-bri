    """
    Mutation data scraper for QRIS transactions
    """
    from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
    from ..models import Mutasi
    from ..parser import IndonesianParser
    from ..config import config
    from ..logger import LoggerMixin

    if TYPE_CHECKING:
        from playwright.async_api import Page, Locator


    class MutasiScraper(LoggerMixin):
        """Scrapes mutation data from QRIS transaction pages"""
        
        def __init__(self):
            super().__init__()
            self.parser = IndonesianParser(config.TIMEZONE)
            self.max_pages = 50  # Safety limit for pagination
        
        async def scrape_mutations(self, page: 'Page') -> List[Mutasi]:
            """
            Scrape all mutations from the mutation page with pagination
            Returns list of Mutasi objects
            """
            try:
                url = config.build_mutasi_url()
                self.log_info("Starting mutation scraping", url=url)
                
                # Navigate to mutation page
                self.log_debug("Navigating to mutation page", url=url)
                await page.goto(url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)  # Wait for page to settle
                
                all_mutations = []
                page_count = 0
                
                while page_count < self.max_pages:
                    page_count += 1
                    self.log_info(f"Scraping page {page_count}")

                    # Wait for transaction elements to load
                    await self._wait_for_transactions(page)

                    # Scrape current page
                    mutations = await self._scrape_current_page(page)
                    if mutations:
                        all_mutations.extend(mutations)
                        self.log_info(f"Found {len(mutations)} mutations on page {page_count}")
                    else:
                        self.log_info(f"No mutations found on page {page_count}")
                    
                    # Try to go to next page
                    has_next = await self._go_to_next_page(page)
                    if not has_next:
                        self.log_info("No more pages available")
                        break
                    
                    # Wait between page loads
                    await page.wait_for_timeout(2000)
                
                self.log_info(f"Scraping completed", 
                            total_mutations=len(all_mutations), 
                            pages_scraped=page_count)
                
                return all_mutations
                
            except Exception as e:
                self.log_error("Error during mutation scraping", error=e)
                # Save debug info for troubleshooting
                try:
                    await self._save_debug_info(page)
                except:
                    pass
                raise
        
        async def _wait_for_table(self, page: 'Page', timeout: int = 10000):
            """Wait for mutation table to be present and loaded"""
            table_selectors = [
                'table#mutasi',
                'table.table',
                'table.mutation-table',
                '.table-responsive table',
                'table:has(thead):has(tbody)',
                'table'
            ]
            
            table_found = False
            for selector in table_selectors:
                try:
                    element = page.locator(selector).first
                    await element.wait_for(state='visible', timeout=timeout)
                    self.log_debug(f"Table found using selector: {selector}")
                    table_found = True
                    break
                except:
                    continue
            
            if not table_found:
                # Wait a bit more and try again
                await page.wait_for_timeout(3000)
                for selector in table_selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.is_visible():
                            table_found = True
                            break
                    except:
                        continue
            
            if not table_found:
                raise Exception("No mutation table found on page")

        async def _wait_for_transactions(self, page: 'Page', timeout: int = 10000):
            """Wait for mutation data (table or cards) to be present"""
            selectors = [
                'table#mutasi',
                'table.table',
                'table.mutation-table',
                '.table-responsive table',
                'table:has(thead):has(tbody)',
                '.flex.text-xs.mb-3.justify-between.bg-white.items-center.border.rounded-xl.py-3.px-4'
            ]

            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    await element.wait_for(state='visible', timeout=timeout)
                    self.log_debug("Transaction elements found", selector=selector)
                    return
                except Exception:
                    continue

            # Additional wait for dynamic data
            await page.wait_for_timeout(3000)
            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible():
                        self.log_debug("Transaction elements found after delay", selector=selector)
                        return
                except Exception:
                    continue

            raise Exception("No transaction data found on page")

        async def _scrape_current_page(self, page: 'Page') -> List[Mutasi]:
            """Scrape mutations from current page"""
            try:
                # Find the table or fallback structure
                table, header_texts = await self._find_table(page)
                if table:
                    mutations = await self._scrape_table_rows(table, header_texts)
                    if mutations:
                        return mutations

                # Fallback: handle card-based transaction list (e.g., BRI Merchant)
                card_selector = '.flex.text-xs.mb-3.justify-between.bg-white.items-center.border.rounded-xl.py-3.px-4'
                card_elements = page.locator(card_selector)
                card_count = await card_elements.count()

                if card_count == 0:
                    self.log_warning("No mutation table or cards found on page")
                    return []

                self.log_info("Falling back to card-based mutation parsing", cards=card_count)

                mutations = []
                for index in range(card_count):
                    card = card_elements.nth(index)
                    try:
                        mutation = await self._parse_card(card)
                        if mutation:
                            mutations.append(mutation)
                    except Exception as exc:
                        self.log_warning("Failed to parse transaction card", index=index, error=str(exc))
                        continue

                return mutations

            except Exception as e:
                self.log_error("Error scraping current page", error=e)
                return []

        async def _scrape_table_rows(self, table: 'Locator', header_texts: List[str]) -> List[Mutasi]:
            """Scrape rows from table structure"""
            # Validate table headers
            if not await self._validate_table_headers(table, header_texts):
                self.log_warning("Table headers don't match expected mutation format")

            rows = table.locator('tbody tr')
            row_count = await rows.count()

            if row_count == 0:
                self.log_info("No data rows found in table")
                return []

            mutations = []
            for i in range(row_count):
                try:
                    row = rows.nth(i)
                    mutation = await self._parse_table_row(row, header_texts)
                    if mutation:
                        mutations.append(mutation)
                except Exception as e:
                    self.log_warning(f"Error parsing row {i}", error=str(e))
                    continue

            return mutations
        
        async def _find_table(self, page: 'Page') -> Tuple[Optional['Locator'], List[str]]:
            """Find the mutation table with flexible selectors

            Returns a tuple of table locator (if found) and list of header texts.
            """
            # Preferred specific selectors
            specific_selectors = [
                'table#mutasi',
                'table.table',
                'table.mutation-table',
                '.table-responsive table',
                'table[data-table="mutasi"]'
            ]
            
            for selector in specific_selectors:
                try:
                    table = page.locator(selector).first
                    if await table.is_visible():
                        header_texts = await self._extract_headers(table)
                        self.log_debug("Table found using specific selector", selector=selector, headers=header_texts)
                        return table, header_texts
                except:
                    continue
            
            # Fallback: find largest table with headers containing mutation keywords
            tables = page.locator('table:has(thead):has(tbody)')
            table_count = await tables.count()
            
            best_table: Optional['Locator'] = None
            best_headers: List[str] = []
            best_score = 0
            
            for i in range(table_count):
                try:
                    table = tables.nth(i)
                    if not await table.is_visible():
                        continue
                    
                    # Get header text
                    header_texts = await self._extract_headers(table)
                    header_count = len(header_texts)
                    
                    if header_count < 3:  # Need at least 3 columns
                        continue
                    
                    # Score based on mutation-related keywords
                    score = 0
                    keywords = ['tanggal', 'date', 'deskripsi', 'description', 'keterangan', 'debit', 'kredit', 'credit', 'saldo', 'balance', 'referensi', 'ref', 'no', 'amount', 'nominal', 'potongan', 'jumlah']
                    for keyword in keywords:
                        if any(keyword in header for header in header_texts):
                            score += 1
                    
                    # Bonus for table size (more rows = likely the main table)
                    rows = table.locator('tbody tr')
                    row_count = await rows.count()
                    score += min(row_count / 10, 5)  # Up to 5 bonus points
                    
                    if score > best_score:
                        best_score = score
                        best_table = table
                        best_headers = header_texts
                        
                except Exception as e:
                    self.log_debug(f"Error evaluating table {i}", error=str(e))
                    continue
            
            if best_table:
                self.log_debug("Best table found", score=best_score, headers=best_headers)
                return best_table, best_headers
            
            self.log_warning("No suitable table found")
            return None, []
        
        async def _validate_table_headers(self, table: 'Locator', headers: Optional[List[str]] = None) -> bool:
            """Validate that table headers contain expected mutation fields"""
            try:
                header_texts = headers or await self._extract_headers(table)
                
                # Check for required keywords
                required_keywords = ['tanggal', 'deskripsi', 'debit', 'kredit']
                found_keywords = 0
                
                for keyword in required_keywords:
                    if any(keyword in header for header in header_texts):
                        found_keywords += 1
                
                is_valid = found_keywords >= 2  # At least 2 required keywords
                
                self.log_debug("Table header validation", 
                            headers=header_texts, 
                            found_keywords=found_keywords, 
                            is_valid=is_valid)
                
                return is_valid
                
            except Exception as e:
                self.log_warning("Error validating table headers", error=str(e))
                return False
        
        async def _parse_table_row(self, row: 'Locator', headers: Optional[List[str]] = None) -> Optional[Mutasi]:
            """Parse a single table row into Mutasi object"""
            try:
                # Get all cell values
                cells = row.locator('td')
                cell_count = await cells.count()
                
                if cell_count < 4:  # Need at least 4 columns for basic data
                    return None
                
                # Extract raw cell values
                raw_values = []
                for i in range(cell_count):
                    cell_text = await cells.nth(i).inner_text()
                    raw_values.append(cell_text.strip())
                
                # Parse fields based on BRI structure
                # The table has wrong structure - "Tanggal" column contains description
                # Real date might be elsewhere or we need to extract from other data
                
                # For BRI, the first column is actually description, not date
                # We need to find the actual date - it might be in a different format
                
                # Try to find date in any column
                tanggal_parsed = None
                tanggal_str = ""
                
                # Look for date patterns in all columns
                for i, value in enumerate(raw_values):
                    if value and len(value) > 8:  # Skip empty/short values
                        # Try to extract date from the value
                        test_date = self.parser.parse_date(value)
                        if test_date:
                            tanggal_parsed = test_date
                            tanggal_str = value
                            break
                
                # If no date found, use current timestamp as fallback
                if not tanggal_parsed:
                    from datetime import datetime
                    import pytz
                    tz = pytz.timezone('Asia/Jakarta')
                    now = datetime.now(tz)
                    tanggal_parsed = now.isoformat()
                    tanggal_str = "current_time"
                    self.log_debug("No date found, using current time", raw_values=raw_values)
                
                # Description (for BRI it's actually in first column)
                deskripsi = self.parser.normalize_text(raw_values[0] if len(raw_values) > 0 else "")
                
                # Filter out unwanted transactions (pencairan, etc)
                excluded_keywords = ['pencairan', 'withdrawal', 'penarikan', 'cash out']
                if any(keyword.lower() in deskripsi.lower() for keyword in excluded_keywords):
                    self.log_debug("Skipping excluded transaction", description=deskripsi)
                    return None
                
                # Find debit and credit columns
                debit = 0.0
                kredit = 0.0
                saldo_akhir = None
                no_referensi = None
                
                # Patterns for BRI and other formats:
                # [Tanggal, Keterangan, Nominal, Potongan, Jumlah] - BRI format
                # [Date, Description, Debit, Credit, Balance, Reference] - standard format
                
                if cell_count >= 5:
                    # BRI format: [Keterangan, Nominal, Potongan, Jumlah, Saldo Akhir]
                    nominal_value = self.parser.parse_number(raw_values[1]) if len(raw_values) > 1 else 0.0
                    potongan_value = self.parser.parse_number(raw_values[2]) if len(raw_values) > 2 else 0.0  
                    jumlah_value = self.parser.parse_number(raw_values[3]) if len(raw_values) > 3 else 0.0
                    
                    # Determine if it's credit or debit based on the data
                    if nominal_value > 0:
                        # If there's a nominal value, it's usually incoming (credit)
                        if potongan_value > 0:
                            # If there's a fee, the net amount is nominal - fee
                            kredit = nominal_value - potongan_value
                        else:
                            kredit = nominal_value
                        debit = 0.0
                    else:
                        # Try alternative parsing for debit transactions
                        debit = abs(jumlah_value) if jumlah_value < 0 else 0.0
                        kredit = jumlah_value if jumlah_value > 0 else 0.0
                    
                    # Use saldo_akhir column if available (column 4 in BRI)
                    if len(raw_values) > 4:
                        saldo_akhir = self.parser.parse_number(raw_values[4])
                        if saldo_akhir == 0.0:
                            saldo_akhir = None
                    
                    # Extract RRN from description as reference
                    import re
                    rrn_match = re.search(r'RRN\s*:\s*([A-Za-z0-9]+)', deskripsi)
                    if rrn_match:
                        no_referensi = rrn_match.group(1)
                            
                elif cell_count == 4:
                    # 4 column layout - try to detect format
                    # Could be [Date, Description, Amount, Type] or [Date, Description, Debit, Credit]
                    val3 = self.parser.parse_number(raw_values[2])
                    val4 = self.parser.parse_number(raw_values[3])
                    
                    # If both are numbers, treat as debit/credit
                    if val3 != 0.0 or val4 != 0.0:
                        debit = val3
                        kredit = val4
                    else:
                        # If one is text, might be amount + type
                        amount = val3
                        type_text = raw_values[3].lower().strip()
                        if 'credit' in type_text or 'cr' in type_text or 'masuk' in type_text:
                            kredit = amount
                        else:
                            debit = amount
                
                # Determine transaction direction
                arah = self.parser.detect_direction(debit, kredit)
                
                # Calculate nominal (absolute value)
                nominal = max(debit, kredit)
                
                # Generate ID
                id_ext = Mutasi.create_id_ext(no_referensi, tanggal_parsed, deskripsi, nominal, arah)
                
                # Ensure we use ISO format for tgl field
                # This is critical for webhook payload date/time parsing
                if not tanggal_parsed:
                    # If parsing failed, use current time as fallback
                    from datetime import datetime
                    import pytz
                    tz = pytz.timezone('Asia/Jakarta')
                    tanggal_parsed = datetime.now(tz).isoformat()
                
                mutation = Mutasi(
                    id_ext=id_ext,
                    tgl=tanggal_parsed,  # Always use ISO format
                    deskripsi=deskripsi,
                    nominal=nominal,
                    saldo_akhir=saldo_akhir,
                    arah=arah,
                    no_referensi=no_referensi,
                    raw=raw_values
                )
                
                self.log_debug("Parsed mutation", 
                            id_ext=id_ext, 
                            date=tanggal_str, 
                            amount=nominal, 
                            direction=arah)
                
                return mutation
                
            except Exception as e:
                self.log_error("Error parsing table row", error=e, raw_values=raw_values if 'raw_values' in locals() else [])
                return None
        
        async def _go_to_next_page(self, page: 'Page') -> bool:
            """Try to navigate to next page, return True if successful"""
            next_selectors = [
                'a:has-text("Next")',
                'a:has-text("Selanjutnya")',
                'button:has-text("Next")',
                'button:has-text("Selanjutnya")',
                '.pagination .next',
                '.pagination a[rel="next"]',
                '.page-next',
                'a[aria-label="Next"]',
                'button[aria-label="Next"]',
                '.pager .next',
                'a:has-text(">")',
                'button:has-text(">")'
            ]
            
            for selector in next_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible() and await element.is_enabled():
                        await element.click()
                        await page.wait_for_timeout(2000)  # Wait for page to load
                        self.log_debug(f"Navigated to next page using: {selector}")
                        return True
                except:
                    continue
            
            # Try pagination with numbers (look for next number)
            try:
                # Get current page number from URL or active pagination
                pagination_links = page.locator('.pagination a, .pager a')
                link_count = await pagination_links.count()
                
                for i in range(link_count):
                    link = pagination_links.nth(i)
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    
                    # Look for numeric pagination
                    if text.strip().isdigit():
                        current_class = await link.get_attribute('class')
                        if current_class and ('active' in current_class or 'current' in current_class):
                            # Found current page, try to click next number
                            if i + 1 < link_count:
                                next_link = pagination_links.nth(i + 1)
                                next_text = await next_link.inner_text()
                                if next_text.strip().isdigit():
                                    await next_link.click()
                                    await page.wait_for_timeout(2000)
                                    self.log_debug("Navigated to next page using pagination number")
                                    return True
                            break
                            
            except Exception as e:
                self.log_debug("Error with numeric pagination", error=str(e))
            
            self.log_debug("No next page found")
            return False
        
        async def _save_debug_info(self, page: 'Page'):
            """Save debug information when scraping fails"""
            try:
                # Save screenshot
                await page.screenshot(path=config.DEBUG_SCREENSHOT, full_page=True)
                
                # Save HTML
                html_content = await page.content()
                with open(config.DEBUG_HTML, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                self.log_info("Debug information saved for troubleshooting")
                
            except Exception as e:
                self.log_error("Failed to save debug information", error=e)

        async def _parse_card(self, card: 'Locator') -> Optional[Mutasi]:
            """Parse transaction card layout into Mutasi"""
            try:
                info_container = card.locator('div.flex-1')
                children = info_container.locator('> *')
                child_count = await children.count()

                if child_count < 3:
                    self.log_warning("Card structure unexpected", child_count=child_count)
                    return None

                # Detail block containing description, masked number, and amount
                detail_block = children.nth(1)
                detail_items = detail_block.locator('p')

                if await detail_items.count() < 3:
                    self.log_warning("Card detail block incomplete")
                    return None

                description_text = await detail_items.nth(0).inner_text()
                masked_number = await detail_items.nth(1).inner_text()
                amount_text = await detail_items.nth(2).inner_text()

                # Status block
                status_block = children.nth(2)
                status_text = await status_block.inner_text()

                # Timestamp (last paragraph within container)
                timestamp_element = info_container.locator('> p').last
                timestamp_text = await timestamp_element.inner_text()

                description = self.parser.normalize_text(description_text)
                masked = self.parser.normalize_text(masked_number)
                status = self.parser.normalize_text(status_text)
                amount = abs(self.parser.parse_number(amount_text))
                arah = self.parser.detect_direction(0.0, amount)

                timestamp_parts = timestamp_text.split('|')
                if len(timestamp_parts) == 2:
                    date_part = timestamp_parts[0].strip()
                    time_part = timestamp_parts[1].strip()
                    combined = f"{date_part} {time_part}"
                else:
                    combined = timestamp_text.strip()

                tanggal_parsed = self.parser.parse_date(combined)
                if not tanggal_parsed and timestamp_parts:
                    tanggal_parsed = self.parser.parse_date(timestamp_parts[0].strip())

                combined_description = self.parser.normalize_text(
                    f"{description} {masked} {status}"
                )

                mutation = Mutasi(
                    id_ext=Mutasi.create_id_ext(None, tanggal_parsed or combined, combined_description, amount, arah),
                    tgl=tanggal_parsed or combined,
                    deskripsi=combined_description,
                    nominal=amount,
                    saldo_akhir=None,
                    arah=arah,
                    no_referensi=None,
                    raw=[description_text, masked_number, amount_text, status_text, timestamp_text]
                )

                return mutation
            except Exception as exc:
                self.log_error("Error parsing transaction card", error=exc)
                return None
