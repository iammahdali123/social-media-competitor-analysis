USE Fashion_Brands10;
GO

DROP TABLE IF EXISTS Dim_Comments;
DROP TABLE IF EXISTS Fact_Posts;
DROP TABLE IF EXISTS Dim_Campaign;
DROP TABLE IF EXISTS Dim_Brand;
DROP TABLE IF EXISTS Dim_Date;

-- ============================================
-- MAKE PK COLUMNS NOT NULL
-- ============================================
ALTER TABLE Dim_Date     ALTER COLUMN Date_Key    INT          NOT NULL;
ALTER TABLE Dim_Brand    ALTER COLUMN Brand_ID    INT          NOT NULL;
ALTER TABLE Dim_Campaign ALTER COLUMN Campaign_ID INT          NOT NULL;
ALTER TABLE Fact_Posts   ALTER COLUMN Post_ID     BIGINT       NOT NULL;
ALTER TABLE Fact_Posts   ALTER COLUMN Brand_ID    INT          NOT NULL;
ALTER TABLE Fact_Posts   ALTER COLUMN Campaign_ID INT          NOT NULL;
ALTER TABLE Fact_Posts   ALTER COLUMN Date_Key    INT          NOT NULL;
ALTER TABLE Dim_Comments ALTER COLUMN Comment_ID  VARCHAR(100) NOT NULL;
ALTER TABLE Dim_Comments ALTER COLUMN Post_ID     BIGINT       NOT NULL;
GO

-- ============================================
-- ADD PRIMARY KEYS
-- ============================================
ALTER TABLE Dim_Date     ADD CONSTRAINT PK_Dim_Date     PRIMARY KEY (Date_Key);
ALTER TABLE Dim_Brand    ADD CONSTRAINT PK_Dim_Brand    PRIMARY KEY (Brand_ID);
ALTER TABLE Dim_Campaign ADD CONSTRAINT PK_Dim_Campaign PRIMARY KEY (Campaign_ID);
ALTER TABLE Fact_Posts   ADD CONSTRAINT PK_Fact_Posts   PRIMARY KEY (Post_ID);
ALTER TABLE Dim_Comments ADD CONSTRAINT PK_Dim_Comments PRIMARY KEY (Comment_ID);
GO

-- ============================================
-- ADD FOREIGN KEYS
-- ============================================
ALTER TABLE Fact_Posts
ADD CONSTRAINT FK_Posts_Brand
FOREIGN KEY (Brand_ID) REFERENCES Dim_Brand(Brand_ID);

ALTER TABLE Fact_Posts
ADD CONSTRAINT FK_Posts_Campaign
FOREIGN KEY (Campaign_ID) REFERENCES Dim_Campaign(Campaign_ID);

ALTER TABLE Fact_Posts
ADD CONSTRAINT FK_Posts_Date
FOREIGN KEY (Date_Key) REFERENCES Dim_Date(Date_Key);

ALTER TABLE Dim_Comments
ADD CONSTRAINT FK_Comments_Post
FOREIGN KEY (Post_ID) REFERENCES Fact_Posts(Post_ID);


-- ============================================
-- VERIFY ROW COUNTS
-- ============================================
SELECT 'Dim_Date'     AS Table_Name, COUNT(*) AS Rows FROM Dim_Date     UNION ALL
SELECT 'Dim_Brand',                  COUNT(*)         FROM Dim_Brand    UNION ALL
SELECT 'Dim_Campaign',               COUNT(*)         FROM Dim_Campaign UNION ALL
SELECT 'Fact_Posts',                 COUNT(*)         FROM Fact_Posts   UNION ALL
SELECT 'Dim_Comments',               COUNT(*)         FROM Dim_Comments;
GO

-- ============================================
-- VERIFY ALL 5 FOREIGN KEYS
-- ============================================
SELECT
    fk.name AS FK_Name,
    tp.name AS Parent_Table,
    cp.name AS Parent_Column,
    tr.name AS Referenced_Table,
    cr.name AS Referenced_Column
FROM sys.foreign_keys fk
JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id;
GO

-- ============================================
-- PREVIEW ALL TABLES
-- ============================================
SELECT TOP 5 * FROM Dim_Date;
SELECT * FROM Dim_Brand;
SELECT * FROM Dim_Campaign;
SELECT TOP 5 * FROM Fact_Posts;
SELECT TOP 5 * FROM Dim_Comments;
GO

-- ============================================
-- QUERY 1: DESCRIPTIVE - Top 3 Brands by Engagement
-- ============================================
SELECT TOP 3
    b.Brand_Name,
    COUNT(p.Post_ID)      AS Total_Posts,
    SUM(p.Likes)          AS Total_Likes,
    SUM(p.Shares)         AS Total_Shares,
    SUM(p.Comments_Count) AS Total_Comments,
    CAST(ROUND(SUM(p.Likes) * 1.0 / COUNT(p.Post_ID), 0) AS INT) AS Avg_Likes_Per_Post
FROM Fact_Posts p
JOIN Dim_Brand b ON p.Brand_ID = b.Brand_ID
GROUP BY b.Brand_Name
ORDER BY Total_Likes DESC;
GO

-- ============================================
-- QUERY 2: DIAGNOSTIC - Campaign Performance with Sentiment
-- ============================================
SELECT
    c.Campaign_Category,
    COUNT(DISTINCT p.Post_ID) AS Total_Posts,
    SUM(p.Likes)              AS Total_Likes,
    SUM(p.Comments_Count)     AS Total_Comments,
    COUNT(CASE WHEN dc.Customer_Intent = 'Sales Inquiry'        THEN 1 END) AS Sales_Inquiries,
    COUNT(CASE WHEN dc.Customer_Intent = 'Restock Request'      THEN 1 END) AS Restock_Requests,
    COUNT(CASE WHEN dc.Customer_Intent = 'Customer Complaint'   THEN 1 END) AS Complaints,
    COUNT(CASE WHEN dc.Customer_Intent = 'Positive Engagement'  THEN 1 END) AS Positive
FROM Fact_Posts p
JOIN Dim_Campaign c   ON p.Campaign_ID = c.Campaign_ID
LEFT JOIN Dim_Comments dc ON p.Post_ID = dc.Post_ID
GROUP BY c.Campaign_Category
ORDER BY Total_Likes DESC;
GO

-- ============================================
-- QUERY 3: TREND - Monthly Likes with 3-Month Rolling Average
-- ============================================
SELECT
    b.Brand_Name,
    d.Year,
    d.Month_Num,
    d.Month_Name,
    COUNT(p.Post_ID)             AS Posts_Count,
    SUM(p.Likes)                 AS Monthly_Likes,
    SUM(p.Comments_Count)        AS Monthly_Comments,
    AVG(SUM(p.Likes)) OVER (
        PARTITION BY b.Brand_Name
        ORDER BY d.Year, d.Month_Num
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS Rolling_3Month_Avg_Likes
FROM Fact_Posts p
JOIN Dim_Brand b ON p.Brand_ID = b.Brand_ID
JOIN Dim_Date  d ON p.Date_Key = d.Date_Key
GROUP BY b.Brand_Name, d.Year, d.Month_Num, d.Month_Name
ORDER BY b.Brand_Name, d.Year, d.Month_Num;
GO