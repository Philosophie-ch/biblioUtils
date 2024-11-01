require 'csv'

# NOTE: hardcoded filenames
report_filename = "refs_html_report.csv"
log_filename = "refs_html.log"

if !File.exist?(report_filename)
  CSV.open(report_filename, 'wb') do |csv|
    csv << ["counter", "login", "references_filename", "further_references_filename", "status", "error_message"]
  end
end

if !File.exist?(log_filename)
  File.open(log_filename, 'w') do |f|
    f.puts "### Log file for refs_html upload ###\n"
  end
end


def log_counter(counter)
  File.open(log_filename, 'a') do |f|
    f.puts "\n\n#{Time.now} --- Processing profile number #{counter}\n"
  end
end

def log_message(msg)
  File.open(log_filename, 'a') do |f|
    f.puts "#{Time.now} --- #{msg}"
  end
end

def log_report(report)
  
  CSV.open(report_filename, 'a') do |csv|
    csv << [report[:counter], report[:login], report[:references_filename], report[:further_references_filename], report[:status], report[:error_message]]
  end
end


# Main
CSV.foreach("refs_instructions.csv", col_sep: ',', headers: true) do |row|
  begin

    # Control
    profile_report = {
      counter: row['counter'] || "",
      login: row['login'] || "",
      references_filename: row['references_filename'] || "",
      further_references_filename: row['further_references_filename'] || "",
      status: "pending",
      error_message: ""
    }

    if login[:counter].blank?
      log_message("\n\nCounter is empty!\n")
    else
      log_counter(profile_report[:counter])
    end

    if profile_report[:login].blank?
      error_message = "Login is empty. Aborting."
      log_message(error_message)
      profile_report[:status] = "error"
      profile_report[:error_message] = error_message
      log_report(profile_report)
      next
    end

    if profile_report[:references_filename].blank?
      error_message = "References filename is empty. Aborting."
      log_message(error_message)
      profile_report[:status] = "error"
      profile_report[:error_message] = error_message
      log_report(profile_report)
      next
    end

    # Processing
    login = profile_report[:login].strip
    references_filename = profile_report[:references_filename].strip
    further_references_filename = profile_report[:further_references_filename].strip

    user = Alchemy::User.find_by(login: login)

    if user.nil?
      error_message = "User '#{login}' not found. Aborting."
      log_message(error_message)
      profile_report[:status] = "error"
      profile_report[:error_message] = error_message
      log_report(profile_report)
      next
    end

    if user.profile.nil?
      error_message = "User '#{login}' has no profile. Aborting."
      log_message(error_message)
      profile_report[:status] = "error"
      profile_report[:error_message] = error_message
      log_report(profile_report)
      next
    end

    # MAIN: Upload HTML content to user profile
    references_html_s = File.read(references_filename)
    user.profile.bibliography_html = references_html_s

    unless further_references_filename.blank?
      further_references_html_s = File.read(further_references_filename)
      user.profile.bibliography_further_references_html = further_references_html_s 
    end

    user.profile.save!
    user.save!

    # Cleanup
    if File.exist?(references_filename)
      File.delete(references_filename)
    end

    if File.exist?(further_references_filename)
      File.delete(further_references_filename)
    end

    profile_report[:status] = "success"
    log_report(profile_report)


  rescue StandardError => e
    error_message = "Unhandled error!: #{e.message}"
    log_message(error_message)
    profile_report[:status] = "error"
    profile_report[:error_message] = error_message

  end

end

