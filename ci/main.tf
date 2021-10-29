terraform {
  backend "s3" {
    bucket = "benchmark-ci-terraform-state"
    key    = "terraform.state"
    region = "eu-west-1"
  }
}

provider "aws" {
  region = "eu-west-2"
}

variable "debian10_x64_ami" {
  type = string
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnet_ids" "all" {
  vpc_id = data.aws_vpc.default.id
}

resource "aws_security_group" "security_group_linux" {
  name        = "ci-ingress-none-egress-all"
  description = "Allow not ingress, egress all"

  vpc_id = data.aws_vpc.default.id

  ingress = [
    {
      cidr_blocks = [
        "0.0.0.0/0",
      ]
      description      = "Incoming SSH Connections"
      from_port        = 0
      ipv6_cidr_blocks = []
      prefix_list_ids  = []
      protocol         = "TCP"
      security_groups  = []
      self             = false
      to_port          = 22
    },
  ]

  egress = [
    {
      cidr_blocks = [
        "0.0.0.0/0",
      ]
      description      = ""
      from_port        = 0
      ipv6_cidr_blocks = []
      prefix_list_ids  = []
      protocol         = "-1"
      security_groups  = []
      self             = false
      to_port          = 0
    },
  ]

  tags = {
    "PURPOSE" = "CI"
  }
}

resource "aws_iam_role" "ci" {
  name = "ci"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF

  tags = {
    "PURPOSE" = "CI"
  }
}

resource "aws_iam_instance_profile" "ci" {
  name = "ci"
  role = aws_iam_role.ci.name
}

# Enable SSM core policy
resource "aws_iam_role_policy_attachment" "scheduler_enable_ssm" {
  role       = aws_iam_role.ci.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_instance" "linux_x64" {
  for_each = {
    "debian-10-x64"    = var.debian10_x64_ami,
  }

  ami           = each.value
  instance_type = "t3.2xlarge"
  vpc_security_group_ids = [
    aws_security_group.security_group_linux.id,
  ]
  iam_instance_profile = aws_iam_instance_profile.ci.name

  associate_public_ip_address = true

  root_block_device {
    delete_on_termination = true
    volume_size           = 100 # GB
    encrypted             = true
  }

  tags = {
    Name = "ci-${each.key}"
  }
}

