# Homebrew formula for Macolint
# This formula can be used in a custom tap
# Usage: brew tap p4puniya/macolint && brew install macolint

class Macolint < Formula
  desc "A terminal-first snippet manager with encrypted local storage"
  homepage "https://github.com/p4puniya/macolint"
  url "https://github.com/p4puniya/macolint/archive/v0.1.0.tar.gz"
  sha256 "0019dfc4b32d63c1392aa264aed2253c1e0c2fb09216f8e2cc269bbfb8bb49b5" # Update with actual SHA256 after first release
  license "MIT"
  head "https://github.com/p4puniya/macolint.git", branch: "main"

  depends_on "rust" => :build

  def install
    system "cargo", "build", "--release", "--locked"
    bin.install "target/release/snip" => "snip"
  end

  test do
    system "#{bin}/snip", "--help"
  end
end

