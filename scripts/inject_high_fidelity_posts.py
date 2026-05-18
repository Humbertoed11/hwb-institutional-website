import sqlite3
import os
from datetime import datetime

# SigmaFidelity™ High-Fidelity Content Injector
# Version 1.1.0 (George / System Architect)

DB_PATH = "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigma_leads.db"

def inject_posts():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Clear existing pending to prevent duplicates during re-formatting
    cursor.execute("DELETE FROM SocialOutbox WHERE status = 'PENDING'")

    posts = [
        ("LinkedIn", "🍋 THE LEMONADE GEMBA | Part 1: The Secret Recipe\n\n**𝐖𝐡𝐲 𝐝𝐨 𝐬𝐨𝐦𝐞 𝐥𝐞𝐦𝐨𝐧𝐚𝐝𝐞 𝐬𝐭𝐚𝐧𝐝𝐬 𝐟𝐚𝐢𝐥 𝐰𝐡𝐢𝐥𝐞 𝐨𝐭𝐡𝐞𝐫𝐬 𝐬𝐜𝐚𝐥𝐞?**\n\nImagine you are 5 years old starting your first business. Day 1 is perfect—customers love the taste. Day 2? You forget the sugar. Your friends walk away. 📉\n\nIn Lean Six Sigma, we call this a **\"𝐃𝐞𝐟𝐞𝐜𝐭.\"** In institutional facility management, it's the difference between a clean site and a liability.\n\nAn **𝐒𝐎𝐏 (𝐒𝐭𝐚𝐧𝐝𝐚𝐫𝐝 𝐎𝐩𝐞𝐫𝐚𝐭𝐢𝐧𝐠 𝐏𝐫𝐨𝐜𝐞𝐝𝐮𝐫𝐞)** is just your \"Secret Recipe\" written in big, bold letters. It ensures that every cup—and every square foot—is identical, every single time.\n\nAt **𝐇𝐖𝐁 𝐂𝐥𝐞𝐚𝐧𝐢𝐧𝐠 𝐒𝐞𝐫𝐯𝐢𝐜𝐞𝐬 𝐋𝐋𝐂**, we don't rely on memory. We rely on **𝐒𝐢𝐠𝐦𝐚𝐅𝐢𝐝𝐞𝐥𝐢𝐭𝐲™ 𝐒𝐎𝐏𝐬** to protect your professional environment.\n\n🚀 **𝐊𝐞𝐲 𝐓𝐚𝐤𝐞𝐚𝐰𝐚𝐲:** Consistency isn't a luxury; it's the foundation of institutional excellence.\n\nHow consistent is your current facility \"recipe\"? Let's audit the waste together.\n\n🔗 **𝐀𝐮𝐝𝐢𝐭 𝐲𝐨𝐮𝐫 𝐟𝐚𝐜𝐢𝐥𝐢𝐭𝐲 𝐡𝐞𝐫𝐞:** http://mop.test:5000/calculator\n\n#SOP #LeanSixSigma #FacilityManagement #InstitutionalExcellence #SigmaFidelity #HWBcleaning"),
        ("LinkedIn", "⚠️ THE LEMONADE GEMBA | Part 2: The Spilled Pitcher\n\n**𝐖𝐡𝐚𝐭 𝐢𝐬 𝐭𝐡𝐞 𝐫𝐞𝐚𝐥 𝐜𝐨𝐬𝐭 𝐨𝐟 \"𝐟𝐨𝐫𝐠𝐞𝐭𝐭𝐢𝐧𝐠 𝐭𝐡𝐞 𝐥𝐢𝐝\"?**\n\nAt a lemonade stand, a spilled pitcher means a sticky mess and zero profit. In a high-stakes facility, \"spilled pitchers\" look like safety violations, role dilution, and employee burnout. 🛑\n\nIn business, this is **𝐂𝐎𝐏𝐐 (𝐂𝐨𝐬𝐭 𝐨𝐟 𝐏𝐨𝐨𝐫 𝐐𝐮𝐚𝐥𝐢𝐭𝐲).** It's the hidden tax you pay for every process that isn't standardized.\n\nAn **𝐒𝐎𝐏** isn't just a list of rules—it's a **𝐒𝐚𝐟𝐞𝐭𝐲 𝐍𝐞𝐭.** It forces the check of the lid, the sugar, and the ice **𝐁𝐄𝐅𝐎𝐑𝐄** the customer arrives.\n\nAt **𝐇𝐖𝐁 𝐂𝐥𝐞𝐚𝐧𝐢𝐧𝐠 𝐒𝐞𝐫𝐯𝐢𝐜𝐞𝐬 𝐋𝐋𝐂**, our mission is to eliminate the \"sticky messes\" of facility operations. We audit the process so you can focus on the result.\n\n💡 **𝐒𝐭𝐫𝐚𝐭𝐞𝐠𝐢𝐜 𝐈𝐧𝐬𝐢𝐠𝐡𝐭:** Precision is the ultimate waste-reduction tool.\n\nIs your organization paying a \"hidden tax\" for process instability?\n\n#ProcessImprovement #QualityControl #ISO9001 #RiskManagement #SigmaFidelity #HWBcleaning"),
        ("LinkedIn", "🏗️ THE LEMONADE GEMBA | Part 3: Scaling the Result\n\n**𝐇𝐨𝐰 𝐝𝐨 𝐲𝐨𝐮 𝐫𝐮𝐧 𝟏𝟎𝟎 𝐥𝐞𝐦𝐨𝐧𝐚𝐝𝐞 𝐬𝐭𝐚𝐧𝐝𝐬 𝐚𝐭 𝐨𝐧𝐜𝐞?**\n\nYou can't be on every corner. You can't supervise every squeeze. 🍋\n\nTo scale, you need **𝐅𝐢𝐝𝐞𝐥𝐢𝐭𝐲.** You must ensure the stand in Arlington tastes exactly like the stand in Dallas. The only way to achieve this is by building a system that works without you.\n\nScaling isn't about working harder; it's about institutionalizing your **\"𝐒𝐞𝐜𝐫𝐞𝐭 𝐑𝐞𝐜𝐢𝐩𝐞\" (𝐒𝐎𝐏)** across every team and every site.\n\nAt **𝐇𝐖𝐁 𝐂𝐥𝐞𝐚𝐧𝐢𝐧𝐠 𝐒𝐞𝐫𝐯𝐢𝐜𝐞𝐬 𝐋𝐋𝐂**, we specialize in high-fidelity management for complex, multi-site operations. We don't just clean; we provide the systemic stability that allows your organization to grow without friction.\n\n🎯 **𝐓𝐡𝐞 𝐆𝐨𝐚𝐥:** Build the system. Scale the result.\n\nReady to transition from \"Manual Management\" to **𝐇𝐢𝐠𝐡-𝐅𝐢𝐝𝐞𝐥𝐢𝐭𝐲** operations?\n\n#BusinessScaling #InstitutionalStandards #FacilityOperations #SigmaFidelity #HWBcleaning #Leadership"),
        ("LinkedIn", "🛡️ THE $200,000 MOP | Strategic Risk\n\n**\"𝐂𝐚𝐧 𝐲𝐨𝐮 𝐣𝐮𝐬𝐭 𝐠𝐫𝐚𝐛 𝐚 𝐦𝐨𝐩 𝐚𝐧𝐝 𝐡𝐚𝐧𝐝𝐥𝐞 𝐭𝐡𝐚𝐭?\"**\n\nIn many DFW facilities, this is seen as \"teamwork.\"\nIn institutional management, it is a **𝐂𝐚𝐫𝐠𝐨 𝐂𝐮𝐥𝐭 𝐫𝐢𝐭𝐮𝐚𝐥** that leads to financial hemorrhaging.\n\n**𝐓𝐡𝐞 𝐆𝐞𝐦𝐛𝐚 (𝐓𝐡𝐞 𝐑𝐞𝐚𝐥 𝐖𝐨𝐫𝐥𝐝):**\nLast month, a worker in Houston was awarded **$𝟐𝟎𝟎,𝟎𝟎𝟎** after raising safety concerns about asbestos handling. The friction started with a simple request to \"help out\" in an area where they weren't properly trained or protected. 🛑\n\nWhen your high-value specialists step out of their lane to handle low-level janitorial tasks, you are creating **𝐏𝐫𝐨𝐜𝐞𝐬𝐬 𝐈𝐧𝐬𝐭𝐚𝐛𝐢𝐥𝐢𝐭𝐲.**\n\nAt **𝐇𝐖𝐁 𝐂𝐥𝐞𝐚𝐧𝐢𝐧𝐠 𝐒𝐞𝐫𝐯𝐢𝐜𝐞𝐬 𝐋𝐋𝐂**, we call this **\"𝐓𝐡𝐞 𝐙𝐞𝐫𝐨-𝐂𝐨𝐬𝐭 𝐈𝐥𝐥𝐮𝐬𝐢𝐨𝐧.\"**\n\n🚀 **𝐓𝐡𝐞 𝐆𝐨𝐚𝐥:** Let your specialists be specialists. We’ll handle the fidelity.\n\n**𝐒𝐭𝐨𝐩 𝐭𝐡𝐞 𝐑𝐢𝐭𝐮𝐚𝐥. 𝐑𝐞𝐬𝐭𝐨𝐫𝐞 𝐭𝐡𝐞 𝐑𝐞𝐬𝐮𝐥𝐭.**\n\n🔗 **𝐈𝐧𝐬𝐭𝐢𝐭𝐮𝐭𝐢𝐨𝐧𝐚𝐥 𝐑𝐞𝐬𝐨𝐮𝐫𝐜𝐞𝐬:** http://mop.test:5000/calculator\n\n#LeanSixSigma #OSHA #FacilityManagement #InstitutionalExcellence #SigmaFidelity #HWBcleaning #CEOLeadership")
    ]

    for platform, content in posts:
        cursor.execute(
            "INSERT INTO SocialOutbox (platform, content, created_at, status) VALUES (?, ?, ?, ?)",
            (platform, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "PENDING")
        )

    conn.commit()
    conn.close()
    print(f"SUCCESS: 4 High-Fidelity LinkedIn posts staged in database.")

if __name__ == "__main__":
    inject_posts()
