CREATE TABLE IF NOT EXISTS business_requirement (
    requirement_id VARCHAR(255) PRIMARY KEY,
    requirement_name VARCHAR(255) NOT NULL,
    requirement_type ENUM('功能需求', '性能需求', '安全需求', '其它需求') NOT NULL,
    parent_requirement VARCHAR(255),
    module VARCHAR(255) NOT NULL,
    requirement_level VARCHAR(255) NOT NULL,
    reviewer VARCHAR(255) NOT NULL,
    estimated_hours INT NOT NULL CHECK (estimated_hours > 0),
    description TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL,
    FOREIGN KEY (parent_requirement)
        REFERENCES business_requirement(requirement_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;